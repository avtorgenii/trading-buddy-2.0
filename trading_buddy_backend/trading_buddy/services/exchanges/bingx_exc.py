from os import getenv

from bingX.perpetual.v2 import PerpetualV2
from bingX.perpetual.v2.types import (Order, OrderType, Side, PositionSide, MarginType)
from bingX.exceptions import ClientError

from trading_buddy_backend.trading_buddy.services.exchanges import math_helper as mh

API_KEY = getenv("API_KEY", "")
SECRET_KEY = getenv("SECRET_KEY", "")
ACCOUNT_NAME = "BingX"

client = PerpetualV2(api_key=API_KEY, secret_key=SECRET_KEY)

# Listeners for cancel prices of tools
listeners_threads = []


def get_deposit_and_risk():
    return db_interface.get_account_details()


def get_account_details():
    """
    Returns the account details.
    :return: A tuple containing balance, unrealized profit, and available margin.
    """
    details = client.account.get_details()['balance']

    deposit, risk = get_deposit_and_risk()

    return deposit, risk, float(details['unrealizedProfit']), float(details['availableMargin'])


def _get_tool_precision_info(tool):
    info = client.market.get_contract_info(tool)
    return {"quantityPrecision": info['quantityPrecision'], "pricePrecision": info['pricePrecision']}


def get_max_leverage(tool):
    info = client.trade.get_leverage(tool)
    return info["maxLongLeverage"], info["maxShortLeverage"]


def calc_position_volume_and_margin(tool, entry_p, stop_p, leverage):
    _, _, _, available_margin = get_account_details()

    precision_info = _get_tool_precision_info(tool)
    quantity_precision = precision_info['quantityPrecision']

    deposit, risk = get_deposit_and_risk()

    volume, margin = mh.calc_position_volume_and_margin(deposit, risk, entry_p, stop_p, available_margin, leverage,
                                                        quantity_precision)
    return volume, margin


def calculate_position_potential_loss_and_profit(tool, entry_p, stop_p, take_ps, volume):
    quantity_precision = _get_tool_precision_info(tool)['quantityPrecision']

    return mh.calculate_position_potential_loss_and_profit(entry_p, stop_p, take_ps, volume, quantity_precision)


def _switch_margin_mode_to_cross(tool):
    client.trade.change_margin_mode(symbol=tool, margin_type=MarginType.CROSSED)


def _place_primary_order(tool, trigger_p, entry_p, stop_p, pos_side, volume):
    order_side = Side.BUY if entry_p > stop_p else Side.SELL

    # If trigger price is not specified, system treats order as limit order
    order_type = OrderType.TRIGGER_LIMIT if trigger_p != 0 else OrderType.LIMIT

    order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                  price=entry_p, stopPrice=trigger_p)
    order_response = client.trade.create_order(order)

    return order_response['order']['orderId']


def place_open_order(tool, trigger_p, entry_p, stop_p, take_profits, move_stop_after, leverage, volume):
    """
    :param tool: Tool to trade
    :param trigger_p: Price level on which to trigger placing limit order
    :param entry_p: Entry level
    :param stop_p: Stop-loss level
    :param take_profits: List of take-profits levels
    :param move_stop_after: After which take stop-loss will be moved to entry level
    :param leverage: Leverage for trade
    :param volume: Entered via modal from frontend if needed
    :return:
    """
    _switch_margin_mode_to_cross(tool)

    pos_side = PositionSide.LONG if entry_p > stop_p else PositionSide.SHORT

    client.trade.change_leverage(tool, pos_side, leverage)

    try:
        _place_primary_order(tool, trigger_p, entry_p, stop_p, pos_side, volume)

        pot_loss, _ = calculate_position_potential_loss_and_profit(tool, entry_p, stop_p, take_profits,
                                                                   volume)

        print(f"POTENTIAL LOSS OF A TRADE: {pot_loss} \n WITH VOLUME: {volume}")

        # Adding primary order info to runtime order book
        rm.add_position(tool, entry_p, stop_p, take_profits, move_stop_after, volume, pot_loss, leverage, trigger_p,
                        take_profits[0])

        return "Primary order placed"
    except ClientError as e:
        if e.error_message == "Insufficient margin":
            return "Please enter volume manually"

        else:
            return "Volume is too small"


def place_stop_loss_order(tool, stop_p, volume, pos_side):
    order_side = Side.SELL if pos_side == "LONG" else Side.BUY
    order_type = OrderType.STOP_MARKET

    order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                  stopPrice=stop_p)
    client.trade.create_order(order)

    print(f"PLACED SL: price: {stop_p}, volume: {volume}")


def cancel_stop_loss_for_tool(tool):
    orders = get_orders_for_tool(tool)

    print(orders)

    stop_order_id = orders['stop']['orderId']

    resp = client.trade.cancel_order(stop_order_id, tool)

    print(f"STOP ORDER CANCELLATION RESPONSE: {resp}")


def cancel_take_profits_for_tool(tool):
    orders = get_orders_for_tool(tool)

    print(orders)

    take_orders = orders['takes']

    for take_order in take_orders:
        take_order_id = take_order['orderId']

        resp = client.trade.cancel_order(take_order_id, tool)

        print(f"TAKE ORDER CANCELLATION RESPONSE: {resp}")


def cancel_primary_order_for_tool(tool, save_to_db=False, only_cancel=False):
    orders = get_orders_for_tool(tool)

    print(orders)

    entry_order_id = orders['entry']['orderId']

    resp = client.trade.cancel_order(entry_order_id, tool)

    print(f"PRIMARY ORDER CANCELLATION RESPONSE: {resp}")

    if not only_cancel:
        if save_to_db:
            rm.close_position(tool)
        else:
            rm.cancel_position(tool)


def place_take_profit_orders(tool, take_profits, cum_volume, pos_side):
    order_side = Side.SELL if pos_side == "LONG" else Side.BUY
    order_type = OrderType.TAKE_PROFIT_MARKET

    quantity_precision = _get_tool_precision_info(tool)['quantityPrecision']

    volumes = mh.calc_take_profits_volumes(cum_volume, quantity_precision, len(take_profits))

    for take_profit, volume in zip(take_profits, volumes):
        order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                      stopPrice=take_profit)

        client.trade.create_order(order)

        print(f"PLACED TP: tp: {take_profit}, volume: {volume}")


def get_orders_for_tool(tool):
    orders = client.trade.get_open_orders(tool)['orders']

    tps = []
    stop = None
    entry = None

    for order in orders:
        if order['type'] == "TAKE_PROFIT_MARKET":
            tps.append(order)
        elif order['type'] == "STOP_MARKET":
            stop = order
        elif order['type'] == "TRIGGER_LIMIT" or order['type'] == "LIMIT":
            entry = order

    return {'entry': entry, 'takes': tps, 'stop': stop}


def get_current_positions_info():
    positions = client.account.get_swap_positions()

    dicts = []

    for position in positions:
        d = {
            'tool': position['symbol'],
            'pos_side': position['positionSide'],
            'leverage': position['leverage'],
            'volume': position['availableAmt'],
            'margin': round(float(position['margin']), 3),
            'avg_open': position['avgPrice'],
            'pnl': mh.floor_to_digits(float(position['unrealizedProfit']) + float(position['realisedProfit']), 4)
        }

        dicts.append(d)

    return dicts


def get_pending_positions_info():
    positions = rm.get_data()

    print(positions)

    dicts = []

    for tool in positions:
        position = positions[tool]
        if position['last_status'] == "NEW":
            d = {
                'tool': tool,
                'entry_price': position['entry_p'],
                'pos_side': position['pos_side'],
                'leverage': position['leverage'],
                'volume': position['primary_volume'],
                'margin': position['entry_p'] * position['primary_volume'] / position['leverage'],
                'trigger_price': position['trigger_p']
            }

            dicts.append(d)

    return dicts


"""DEBUG"""
if __name__ == '__main__':
    #place_open_order("OP-USDT", 0, 1.803, 1.7776, [1.8348, 1.85], 1, 50, 1)
    res = get_account_details()

    print(res)
