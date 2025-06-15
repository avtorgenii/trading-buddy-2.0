from decimal import Decimal
from typing import List, Dict, Tuple, Any
import threading

from bingX.perpetual.v2 import PerpetualV2
from bingX.perpetual.v2.types import (Order, OrderType, Side, PositionSide, MarginType)
from bingX.exceptions import ClientError
from ...models import Account, User, Position, Trade, Tool

from ..exchanges import math_helper as mh
from .listeners import BingXOrderListenerManager, BingXPriceListener


class Exchange:
    """
    Base Exchange class. Enforces one exchange instance per account.
    Subclasses must define `exchange_name`.
    """

    _instances: Dict[Any, 'Exchange'] = {}
    _lock = threading.Lock()

    exchange_name: str = "BASE_EXCHANGE"  # Should be overridden in subclasses

    def __new__(cls, account: Any, *args, **kwargs):
        if cls.exchange_name == "BASE_EXCHANGE":
            raise TypeError("Cannot instantiate the base Exchange class directly. Use a subclass.")

        if not account:
            raise ValueError("An account must be provided to instantiate an Exchange.")

        with cls._lock:
            if account not in cls._instances:
                instance = super().__new__(cls)
                cls._instances[account] = instance
                instance._initialized = False
            else:
                instance = cls._instances[account]
                instance._initialized = True

            return instance

    def __init__(self, account: Any, *args, **kwargs):
        if self._initialized:
            return  # Skip re-initialization

        self._account = account
        self._user = account.user

        self.API_KEY = self._account.api_key
        self.SECRET_KEY = self._account.secret_key

    ##### TWO PROPERTIES BELOW ARE ABSOLUTELY CRUCIAL FOR PREVENTING DATA STALENESS, use only them in code #####
    @property
    def fresh_account(self):
        return Account.objects.get(pk=self._account.pk)

    @property
    def fresh_user(self):
        return User.objects.get(pk=self._user.pk)

    def get_account_details(self) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        raise NotImplementedError("Method not implemented")

    ##### ALL FUNCTIONS WHICH GET AS A PARAM TOOL NAME ASSUME THAT IT IS ALREADY WITH APPROPRIATE EXCHANGE SUFFIX #####

    def get_max_leverage(self, tool: str) -> Tuple[int, int]:
        raise NotImplementedError("Method not implemented")

    def calc_position_volume_and_margin(self, tool: str, entry_p: Decimal, stop_p: Decimal, leverage: Decimal) -> Tuple[
        Decimal, Decimal]:
        raise NotImplementedError("Method not implemented")

    def place_open_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                         take_profits: List[Decimal],
                         move_stop_after: int, leverage: int, volume: Decimal) -> str:
        raise NotImplementedError("Method not implemented")

    def place_stop_loss_order(self, tool: str, stop_p: Decimal, volume: Decimal, pos_side: PositionSide) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_stop_loss_for_tool(self, tool: str) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_take_profits_for_tool(self, tool: str) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False) -> None:
        raise NotImplementedError("Method not implemented")

    def place_take_profit_orders(self, tool: str, take_profits: List[Decimal], cum_volume: Decimal,
                                 pos_side: PositionSide) -> None:
        raise NotImplementedError("Method not implemented")

    def close_by_market(self, tool: str) -> str:
        raise NotImplementedError("Method not implemented")

    def get_orders_for_tool(self, tool: str) -> Dict[str, Any]:
        raise NotImplementedError("Method not implemented")

    def get_current_positions_info(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Method not implemented")


class BingXExc(Exchange):
    """
    BingX Exchange implementation as a Singleton per-account class.
    Tool format: "<name>-USDT"
    """
    exchange_name = "BingX"

    def __init__(self, account: Account, *args, **kwargs):
        """
        Initialize the BingX exchange with API credentials.
        """
        super().__init__(account, *args, **kwargs)

        if self._initialized:
            return

        self.client = PerpetualV2(api_key=self.API_KEY, secret_key=self.SECRET_KEY)

        # Listeners
        self.price_listeners_and_threads = {}
        self.order_listener_manager = None
        self.order_listener_manager_thread = None

        self.restore_price_listeners()
        self.create_order_listener_manager_in_thread()

        # Mark the instance as fully initialized
        self._initialized = True

    def create_price_listener_in_thread(self, tool_name):
        p_listener = BingXPriceListener(tool_name, self)

        price_listener_thread = threading.Thread(target=p_listener.listen_for_events)
        # Daemon threads exit automatically when the main program exits.
        price_listener_thread.daemon = True
        price_listener_thread.start()

        self.price_listeners_and_threads[tool_name] = [p_listener, price_listener_thread]

    def restore_price_listeners(self):
        """
        After crash of the server, it will still be able to restore all listeners.
        :return:
        """
        # Delete all exising price listeners
        for listener, thread in self.price_listeners_and_threads:
            try:
                tool_name = listener.tool.name
                listener.stop_listening()
                thread.exit()

                del self.price_listeners_and_threads[tool_name]
            except Exception as e:
                print("Price listener already deleted")

        # Create new ones for each tool
        positions = self.fresh_account.positions.all()

        # Recreate price listener only if position os still pending
        for pos in positions:
            if pos.last_status == "NEW":
                self.create_price_listener_in_thread(pos.tool.name)

    def delete_price_listener(self, tool_name):
        try:
            listener, thread = self.price_listeners_and_threads[tool_name]
            listener.stop_listening()
            thread.exit()

            del self.price_listeners_and_threads[tool_name]
        except Exception as e:
            print("Price listener already deleted")

    def _create_order_listener_manager(self):
        self.order_listener_manager = BingXOrderListenerManager(self)

    def create_order_listener_manager_in_thread(self):
        listener_thread = threading.Thread(target=self._create_order_listener_manager)
        # Daemon threads exit automatically when the main program exits.
        listener_thread.daemon = True
        listener_thread.start()

        self.order_listener_manager_thread = listener_thread

    def get_deposit_and_risk(self) -> Tuple[Decimal, Decimal]:
        """
        Returns the deposit and risk % values from the database.
        :return: A tuple containing deposit and risk %.
        """
        return self.fresh_user.deposit, self.fresh_account.risk_percent

    def get_account_details(self) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """
        Returns the account details.
        :return: A tuple containing deposit, risk %, unrealized profit, and available margin.
        """
        details = self.client.account.get_details()['balance']

        deposit, risk = self.get_deposit_and_risk()

        return deposit, risk, Decimal(details['unrealizedProfit']), Decimal(details['availableMargin'])

    def _get_tool_precision_info(self, tool: str) -> Dict[str, int]:
        """
        Gets precision information for a trading pair.
        :param tool: The trading pair.
        :return: Dictionary with quantity and price precision.
        """
        info = self.client.market.get_contract_info(tool)
        return {"quantityPrecision": info['quantityPrecision'], "pricePrecision": info['pricePrecision']}

    def get_max_leverage(self, tool: str) -> Tuple[int, int]:
        """
        Returns the maximum leverage for a trading pair.
        :param tool: The trading pair.
        :return: A tuple containing the maximum long leverage and maximum short leverage.
        """
        info = self.client.trade.get_leverage(tool)
        return info["maxLongLeverage"], info["maxShortLeverage"]

    def calc_position_volume_and_margin(self, tool: str, entry_p: Decimal, stop_p: Decimal, leverage: int) -> Tuple[
        Decimal, Decimal]:
        """
        Calculates the position volume and margin.
        :param tool: The trading pair.
        :param entry_p: Entry price.
        :param stop_p: Stop loss price.
        :param leverage: Leverage for the trade.
        :return: A tuple containing the calculated volume and margin.
        """
        _, _, _, available_margin = self.get_account_details()

        precision_info = self._get_tool_precision_info(tool)
        quantity_precision = precision_info['quantityPrecision']

        deposit, risk = self.get_deposit_and_risk()

        volume, margin = mh.calc_position_volume_and_margin(deposit, risk, entry_p, stop_p, available_margin, leverage,
                                                            quantity_precision)

        return volume, margin

    def calc_position_margin(self, entry_p: Decimal, volume: Decimal, leverage: int) -> Decimal:
        """
        Calculates the position margin.
        :param entry_p: Entry price.
        :param volume: Position volume.
        :param leverage: Leverage for the trade.
        :return: Margin required to open position.
        """

        return mh.calculate_position_margin(entry_p, volume, leverage)

    def calculate_position_potential_loss_and_profit(self, tool: str, entry_p: Decimal, stop_p: Decimal,
                                                     take_ps: List[Decimal], volume: Decimal) -> Tuple[
        Decimal, Decimal]:
        """
        Calculates the potential loss and profit for a position.
        :param tool: The trading pair.
        :param entry_p: Entry price.
        :param stop_p: Stop loss price.
        :param take_ps: List of take profit prices.
        :param volume: Trading volume.
        :return: A tuple containing the potential loss and profit.
        """

        quantity_precision = self._get_tool_precision_info(tool)['quantityPrecision']

        return mh.calculate_position_potential_loss_and_profit(entry_p, stop_p, take_ps, volume, quantity_precision)

    def _switch_margin_mode_to_cross(self, tool: str) -> None:
        """
        Switches the margin mode to cross for a tool
        :param tool: The tool name
        """
        self.client.trade.change_margin_mode(symbol=tool, margin_type=MarginType.CROSSED)

    def _place_primary_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                             pos_side: PositionSide, volume: Decimal) -> str:
        """
        Places a primary order.
        :param tool: The trading pair.
        :param trigger_p: Trigger price.
        :param entry_p: Entry price.
        :param stop_p: Stop loss price.
        :param pos_side: Position side (LONG/SHORT).
        :param volume: Trading volume.
        :return: Order ID.
        """
        order_side = Side.BUY if entry_p > stop_p else Side.SELL

        # If trigger price is not specified, system treats order as a limit order
        order_type = OrderType.TRIGGER_LIMIT if trigger_p != 0 else OrderType.LIMIT

        order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                      price=entry_p, stopPrice=trigger_p)
        order_response = self.client.trade.create_order(order)

        return order_response['order']['orderId']

    def place_open_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                         take_profits: List[Decimal], move_stop_after: int, leverage: int,
                         volume: Decimal) -> str:
        """
        Places an open order.
        :param tool: Tool to trade
        :param trigger_p: Price level on which to trigger placing limit order
        :param entry_p: Entry level
        :param stop_p: Stop-loss level
        :param take_profits: List of take-profits levels
        :param move_stop_after: After which take stop-loss will be moved to entry level
        :param leverage: Leverage for trade
        :param volume: Entered via modal from frontend if needed
        :return: Status message
        """
        deposit, _ = self.get_deposit_and_risk()
        if deposit > 0:
            self._switch_margin_mode_to_cross(tool)

            pos_side = PositionSide.LONG if entry_p > stop_p else PositionSide.SHORT

            max_long_leverage, max_short_leverage = self.get_max_leverage(tool)

            if leverage <= 0:
                return "Invalid leverage selected"

            if (
                    (pos_side == PositionSide.LONG and leverage > max_long_leverage)
                    or (pos_side == PositionSide.SHORT and leverage > max_short_leverage)
            ):
                return "Invalid leverage selected"

            self.client.trade.change_leverage(tool, pos_side, leverage)

            try:
                self._place_primary_order(tool, trigger_p, entry_p, stop_p, pos_side, volume)

                pot_loss, _ = self.calculate_position_potential_loss_and_profit(tool, entry_p, stop_p, take_profits,
                                                                                volume)

                print(f"POTENTIAL LOSS OF A TRADE: {pot_loss} \n WITH VOLUME: {volume}")

                # Creating trade and linked position in db
                Trade.create_trade(pos_side.value, self.fresh_account, tool, pot_loss / deposit, pot_loss, leverage,
                                   trigger_p,
                                   entry_p,
                                   stop_p, take_profits, move_stop_after, volume)

                self.create_price_listener_in_thread(tool)

                return "Primary order placed"

            except ClientError as e:
                return e.error_message

        else:
            return "Deposit must be positive"

    def place_stop_loss_order(self, tool: str, stop_p: Decimal, volume: Decimal, pos_side: PositionSide) -> None:
        """
        Places a stop loss order.
        :param tool: The tool name.
        :param stop_p: Stop loss price.
        :param volume: Trading volume.
        :param pos_side: Position side (LONG/SHORT).
        """
        order_side = Side.SELL if pos_side == "LONG" else Side.BUY
        order_type = OrderType.STOP_MARKET

        order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume,
                      type=order_type,
                      stopPrice=stop_p)
        self.client.trade.create_order(order)

        print(f"PLACED SL: price: {stop_p}, volume: {volume}")

    def cancel_stop_loss_for_tool(self, tool: str) -> None:
        """
        Cancels the stop loss order for a tool
        :param tool: Tool name
        """
        orders = self.get_orders_for_tool(tool)
        print(f"Orders: {orders}")

        stop_order = orders.get('stop')
        if not stop_order:
            print("No stop order found.")
            return

        stop_order_id = stop_order.get('orderId')
        if not stop_order_id:
            print("No stop order ID found.")
            return

        resp = self.client.trade.cancel_order(stop_order_id, tool)
        print(f"STOP ORDER CANCELLATION RESPONSE: {resp}")

    def cancel_take_profits_for_tool(self, tool: str) -> None:
        """
        Cancels all take profit orders for a trading pair.
        :param tool: The trading pair.
        """
        orders = self.get_orders_for_tool(tool)
        print(orders)

        take_orders = orders.get('takes')
        if not take_orders:
            print("No take profit orders found.")
            return

        for take_order in take_orders:
            take_order_id = take_order.get('orderId')
            if not take_order_id:
                print(f"Take profit order missing 'orderId': {take_order}")
                continue

            resp = self.client.trade.cancel_order(take_order_id, tool)
            print(f"TAKE ORDER CANCELLATION RESPONSE: {resp}")

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False,
                                      reason: str = None) -> None:
        """
        Cancels the primary order for a trading pair.
        :param reason: Reason for canceling position.
        :param tool: The trading pair.
        :param save_to_db: Whether to save the cancellation to the database.
        :param only_cancel: Whether to only cancel the order without updating db.
        """

        orders = self.get_orders_for_tool(tool)

        print(orders)

        entry_order_id = orders['entry']['orderId']

        resp = self.client.trade.cancel_order(entry_order_id, tool)

        print(f"PRIMARY ORDER CANCELLATION RESPONSE: {resp}")

        if not only_cancel:
            # last() IS CRUCIAL, as we only fetch trades by name of tool, and not some unique ID within whole account
            trade = Trade.objects.filter(account=self.fresh_account, tool__name=tool).last()
            if save_to_db:
                # For positions closing, cancellation via overhigh/overlow and automatic cancellation of orders when reached take-profit level, their data is being saved into database
                pos = Position.objects.filter(pk=trade.position.pk).first()
                pos.close_position(reason)
            else:
                # For manual cancellation of position, data doesn't go to db
                trade.delete()  # position will be auto deleted, see models.py for this

        self.delete_price_listener(tool)

    def place_take_profit_orders(self, tool: str, take_profits: List[Decimal], cum_volume: Decimal,
                                 pos_side: PositionSide) -> None:
        """
        Places take profit orders for a trading pair.
        :param tool: The trading pair.
        :param take_profits: List of take profit prices.
        :param cum_volume: Cumulative volume.
        :param pos_side: Position side (LONG/SHORT).
        """

        order_side = Side.SELL if pos_side == "LONG" else Side.BUY
        order_type = OrderType.TAKE_PROFIT_MARKET

        quantity_precision = self._get_tool_precision_info(tool)['quantityPrecision']

        volumes = mh.calc_take_profits_volumes(cum_volume, quantity_precision, len(take_profits))

        for take_profit, volume in zip(take_profits, volumes):
            order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                          stopPrice=take_profit)

            self.client.trade.create_order(order)

            print(f"PLACED TP: {take_profit}, volume: {volume}")

    def close_by_market(self, tool: str) -> str:
        trade = Trade.objects.filter(account=self.fresh_account, tool__name=tool).last()

        pos = Position.objects.filter(pk=trade.position.pk).first()

        order_side = Side.SELL if pos.side == "LONG" else Side.BUY
        order = Order(symbol=tool, side=order_side, positionSide=pos.side, quantity=pos.current_volume)

        try:
            self.client.trade.close_order(order)
            return "Closing market order placed successfully"
        except Exception as e:
            return f"Position wasn't closed: {e}"

    def get_orders_for_tool(self, tool: str) -> Dict[str, Any]:
        """
        Gets all open orders for a trading pair.
        :param tool: The trading pair.
        :return: Dictionary containing entry, take profit, and stop orders.
        """
        orders = self.client.trade.get_open_orders(tool)['orders']

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

    def get_current_positions_info(self) -> List[Dict[str, Any]]:
        """
        Gets information about all current positions.
        :return: List of dictionaries containing position information.
        """
        positions = self.client.account.get_swap_positions()

        dicts = []

        for position in positions:
            tool_name = position['symbol']
            try:
                db_pos = self.fresh_account.positions.get(tool__name=tool_name)
            except Position.DoesNotExist as e:
                print(str(e) + f" for {tool_name}: there are open positions on server, but they aren't in database.")
                continue

            trade = db_pos.trade

            d = {
                'tool': tool_name,
                'pos_side': position['positionSide'],
                'leverage': str(position['leverage']),
                'volume': str(position['availableAmt']),
                'margin': str(round(Decimal(position['margin']), 3)),
                'avg_open': str(position['avgPrice']),
                'current_pnl_risk_reward_ratio':
                    str(mh.floor_to_digits(
                        (Decimal(position['unrealizedProfit']) + Decimal(position['realisedProfit'])) / trade.risk_usd,
                        4)),
                'realized_pnl': str(mh.floor_to_digits(Decimal(position['realisedProfit']), 4)),
                'current_pnl':
                    str(mh.floor_to_digits(
                        Decimal(position['unrealizedProfit']) + Decimal(position['realisedProfit']),
                        4)),
                'open_date': str(db_pos.start_time)
            }

            dicts.append(d)

        return dicts

    def get_pending_positions_info(self) -> List[Dict[str, Any]]:
        """
        Gets information about all pending positions.
        :return: List of dictionaries containing pending position information.
        """
        positions = Position.objects.filter(account=self.fresh_account).all()

        dicts = []

        for pos in positions:
            if pos.last_status == "NEW":
                d = {
                    'tool': pos.tool.name,
                    'entry_price': str(pos.entry_price),
                    'pos_side': pos.side,
                    'leverage': str(pos.leverage),
                    'volume': str(pos.primary_volume),
                    'margin': str(round(Decimal(pos.entry_price * pos.primary_volume / pos.leverage), 3)),
                    'trigger_price': str(pos.trigger_price),
                    'cancel_levels': [str(level) if level is not None else level for level in pos.cancel_levels],
                }

                dicts.append(d)

        return dicts
