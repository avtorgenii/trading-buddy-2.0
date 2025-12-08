import json
from decimal import Decimal
from typing import List, Tuple, Any
import threading

from django.utils import timezone
from loguru import logger
import time

import bingX.exceptions
from bingX.perpetual.v2 import PerpetualV2
from bingX.perpetual.v2.types import (Order, OrderType, Side, PositionSide, MarginType, StopLossOrder, TakeProfitOrder,
                                      HistoryOrder)
from ...models import Account, User, Position, Trade

from ..exchanges import math_helper as mh
from .listeners import BingXPriceListener


def format_dict_for_log(dict_data: dict | list) -> str:
    return json.dumps(dict_data, indent=2).replace("{", '').replace("}", '')


class Exchange:
    """
    Base Exchange class. Enforces one exchange instance per account.
    Subclasses must define `exchange_name`.
    """

    _instances: dict[Any, 'Exchange'] = {}
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

    @classmethod
    def check_account_validity(cls, api_key, secret_key) -> bool:
        raise NotImplementedError("Method not implemented")

    def get_account_details(self) -> Tuple[bool, str, Decimal, Decimal, Decimal | None, Decimal | None]:
        raise NotImplementedError("Method not implemented")

    ##### ALL FUNCTIONS WHICH GET AS A PARAM TOOL NAME ASSUME THAT IT IS ALREADY WITH the APPROPRIATE EXCHANGE SUFFIX #####
    def create_price_listener_in_thread(self, tool_name: str):
        raise NotImplementedError("Method not implemented")

    def restore_price_listeners(self):
        raise NotImplementedError("Method not implemented")

    def delete_price_listener(self, tool_name: str):
        raise NotImplementedError("Method not implemented")

    def get_max_leverage(self, tool: str) -> Tuple[bool, str, int | None, int | None]:
        raise NotImplementedError("Method not implemented")

    def _get_tool_precision_info(self, tool: str) -> Tuple[bool, dict[str, int]]:
        raise NotImplementedError("Method not implemented")

    def calc_position_volume_and_margin(self, tool: str, entry_p: Decimal, stop_p: Decimal, leverage: Decimal) -> tuple[
                                                                                                                      Decimal, Decimal] | \
                                                                                                                  tuple[
                                                                                                                      None, None]:
        raise NotImplementedError("Method not implemented")

    def calculate_position_potential_loss_and_profit(self, tool: str, entry_p: Decimal, stop_p: Decimal,
                                                     take_ps: List[Decimal], volume: Decimal) -> tuple[
                                                                                                     Decimal, Decimal] | \
                                                                                                 tuple[None, None]:
        raise NotImplementedError("Method not implemented")

    def place_open_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                         take_profits: List[Decimal],
                         move_stop_after: int, leverage: int, volume: Decimal) -> Tuple[bool, str]:
        raise NotImplementedError("Method not implemented")

    def place_stop_loss_order(self, tool: str, stop_p: Decimal, volume: Decimal, pos_side: PositionSide) -> Tuple[
        bool, str]:
        raise NotImplementedError("Method not implemented")

    def cancel_stop_loss_for_tool(self, tool: str) -> Tuple[bool, str]:
        raise NotImplementedError("Method not implemented")

    def cancel_take_profits_for_tool(self, tool: str) -> Tuple[bool, str]:
        raise NotImplementedError("Method not implemented")

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False) -> Tuple[
        bool, str]:
        raise NotImplementedError("Method not implemented")

    def place_take_profit_orders(self, tool: str, take_profits: List[Decimal], cum_volume: Decimal,
                                 pos_side: PositionSide) -> Tuple[bool, str]:
        raise NotImplementedError("Method not implemented")

    def close_by_market(self, tool: str) -> Tuple[bool, str]:
        raise NotImplementedError("Method not implemented")

    def get_orders_for_tool(self, tool: str) -> Tuple[bool, str, dict[str, Any]]:
        raise NotImplementedError("Method not implemented")

    def get_current_positions_info(self) -> Tuple[bool, str, List[dict[str, Any]]]:
        raise NotImplementedError("Method not implemented")

    def get_pending_positions_info(self) -> List[dict[str, Any]]:
        raise NotImplementedError("Method not implemented")

    def get_open_orders(self, position_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        raise NotImplementedError("Method not implemented")

    def get_current_positions(self) -> list[dict[str, Any]]:
        raise NotImplementedError("Method not implemented")

    def get_position_result(self, db_pos: Position) -> dict[str, Any]:
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

        # Reinitialize if account's api key has been changed
        if self._initialized and self.fresh_account.api_key == self.API_KEY and self.fresh_account.secret_key == self.SECRET_KEY:
            return

        self.client = PerpetualV2(api_key=self.API_KEY, secret_key=self.SECRET_KEY)

        # Listeners
        self.price_listeners_and_threads = {}
        self.order_listener_manager = None
        self.order_listener_manager_thread = None

        self.restore_price_listeners()
        # self.create_order_listener_manager_in_thread()

        # Mark the instance as fully initialized
        self._initialized = True

    def create_price_listener_in_thread(self, tool_name: str):
        p_listener = BingXPriceListener(tool_name, self)

        price_listener_thread = threading.Thread(target=p_listener.listen_for_events)
        # Daemon threads exit automatically when the main program exits.
        price_listener_thread.daemon = True
        price_listener_thread.start()

        self.price_listeners_and_threads[tool_name] = [p_listener, price_listener_thread]
        logger.info(f"Created price listener for {tool_name}")

    def restore_price_listeners(self):
        """
        After crash of the server, it will still be able to restore all listeners.
        :return:
        """
        logger.info("Restoring price listeners")
        # Delete all exising price listeners
        for listener, thread in self.price_listeners_and_threads:
            try:
                tool_name = listener.tool.name
                listener.stop_listening()
                del self.price_listeners_and_threads[tool_name]
            except Exception as e:
                logger.warning("Price listener already deleted")

        # Create new ones for each pending position
        positions = self.fresh_account.positions.all()

        # Recreate price listener only if position is still pending
        for pos in positions:
            if pos.last_status == "NEW":
                self.create_price_listener_in_thread(pos.tool.name)

    def delete_price_listener(self, tool_name: str):
        try:
            listener, thread = self.price_listeners_and_threads[tool_name]
            listener.stop_listening()
            del self.price_listeners_and_threads[tool_name]
        except Exception as e:
            logger.warning("Price listener was already deleted")

    @classmethod
    def check_account_validity(cls, api_key, secret_key) -> bool:
        """Exchange instance will self destroy in case of invalid account credentials."""
        try:
            client = PerpetualV2(api_key=api_key, secret_key=secret_key)
            client.other.generate_listen_key()
        except bingX.exceptions.ServerError as e:
            logger.warning("Error from server checking account validity")
            return False
        except bingX.exceptions.ClientError as e:
            logger.warning("Error from client checking account validity")
            return False

        return True

    def get_deposit_and_risk(self) -> Tuple[Decimal, Decimal]:
        """
        Returns the deposit and risk % values from the database.
        :return: A tuple containing deposit and risk %.
        """
        return self.fresh_user.deposit, self.fresh_account.risk_percent

    def get_account_details(self) -> Tuple[bool, str, Decimal, Decimal, Decimal | None, Decimal | None]:
        """
        Returns the account details.
        :return: A tuple containing deposit, risk %, unrealized profit, and available margin.
        """
        deposit, risk = self.get_deposit_and_risk()

        try:
            details = self.client.account.get_details()['balance']
            return True, "Successfully retrieved all account details", deposit, risk, Decimal(
                details['unrealizedProfit']), Decimal(details['availableMargin'])
        except Exception as e:
            logger.warning("Failed to get account details")
            return False, "Exchange side account details: unrealized and realized profits were unable to retrieved", deposit, risk, None, None

    def _get_tool_precision_info(self, tool: str) -> Tuple[bool, dict[str, int]]:
        """
        Gets precision information for a trading pair.
        :param tool: The trading pair.
        :return: dictionary with quantity and price precision.
        """
        try:
            info = self.client.market.get_contract_info(tool)
            return True, {"quantityPrecision": info['quantityPrecision'], "pricePrecision": info['pricePrecision']}
        except Exception as e:
            logger.warning(f"Failed to get tool precision info for {tool}")
            return False, {}

    def get_max_leverage(self, tool: str) -> Tuple[bool, str, int | None, int | None]:
        """
        Returns the maximum leverage for a trading pair.
        :param tool: The trading pair.
        :return: A tuple containing the maximum long leverage and maximum short leverage.
        """
        try:
            info = self.client.trade.get_leverage(tool)
            return True, "Successfully retrieved leverage limits", info["maxLongLeverage"], info["maxShortLeverage"]
        except Exception as e:
            logger.warning(f'Failed to get max leverage info for {tool}')
            return False, "Failed to retrieve leverage limits", None, None

    def calc_position_volume_and_margin(self, tool: str, entry_p: Decimal, stop_p: Decimal, leverage: int) -> tuple[
                                                                                                                  Decimal, Decimal] | \
                                                                                                              tuple[
                                                                                                                  None, None]:
        """
        Calculates the position volume and margin.
        :param tool: The trading pair.
        :param entry_p: Entry price.
        :param stop_p: Stop loss price.
        :param leverage: Leverage for the trade.
        :return: A tuple containing the calculated volume and margin.
        """
        acc_success, _, _, _, _, available_margin = self.get_account_details()

        prec_success, precision_info = self._get_tool_precision_info(tool)
        if acc_success and prec_success:
            quantity_precision = precision_info['quantityPrecision']

            deposit, risk = self.get_deposit_and_risk()

            volume, margin = mh.calc_position_volume_and_margin(deposit, risk, entry_p, stop_p, available_margin,
                                                                leverage,
                                                                quantity_precision)

            return volume, margin
        else:
            return None, None

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
                                                     take_ps: List[Decimal], volume: Decimal) -> tuple[
                                                                                                     Decimal, Decimal] | \
                                                                                                 tuple[None, None]:
        """
        Calculates the potential loss and profit for a position.
        :param tool: The trading pair.
        :param entry_p: Entry price.
        :param stop_p: Stop loss price.
        :param take_ps: List of take profit prices.
        :param volume: Trading volume.
        :return: A tuple containing the potential loss and profit.
        """

        success, precision_info = self._get_tool_precision_info(tool)
        if success:
            quantity_precision = precision_info['quantityPrecision']

            return mh.calculate_position_potential_loss_and_profit(entry_p, stop_p, take_ps, volume, quantity_precision)
        else:
            return None, None

    def _switch_margin_mode_to_cross(self, tool: str) -> None:
        """
        Switches the margin mode to cross for a tool
        :param tool: The tool name
        """
        try:
            self.client.trade.change_margin_mode(symbol=tool, margin_type=MarginType.CROSSED)
        except Exception as e:
            logger.warning('Failed to switch to cross margin mode')

    def _place_primary_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                             take_profit_p: Decimal,
                             pos_side: PositionSide, volume: Decimal) -> Tuple[bool, str]:
        """
        Places a primary order.
        :param tool: The trading pair.
        :param trigger_p: Trigger price.
        :param entry_p: Entry price.
        :param stop_p: Stop-loss price.
        :param take_profit_p: First take-profit price.
        :param pos_side: Position side (LONG/SHORT).
        :param volume: Trading volume.
        :return: Order ID.
        """
        order_side = Side.BUY if entry_p > stop_p else Side.SELL

        # If trigger price is not specified, system treats order as a limit order
        order_type = OrderType.TRIGGER_LIMIT if trigger_p != 0 else OrderType.LIMIT

        stop_loss_order = StopLossOrder(stopPrice=stop_p, price=stop_p)
        take_profit_order = TakeProfitOrder(stopPrice=take_profit_p, price=take_profit_p)

        primary_order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                              price=entry_p, stopPrice=trigger_p, stopLoss=stop_loss_order,
                              takeProfit=take_profit_order)
        try:
            order_response = self.client.trade.create_order(primary_order)

            return True, order_response['order']['orderId']
        except Exception as e:
            logger.exception(f'Failed to place primary order for {order_side} {tool} on {entry_p}')
            return False, str(e)

    def place_open_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                         take_profits: List[Decimal], move_stop_after: int, leverage: int,
                         volume: Decimal) -> Tuple[bool, str]:
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
        if deposit <= 0:
            return False, "Deposit must be positive"
        else:
            self._switch_margin_mode_to_cross(tool)

            pos_side = PositionSide.LONG if entry_p > stop_p else PositionSide.SHORT

            success, msg, max_long_leverage, max_short_leverage = self.get_max_leverage(tool)

            if not success:
                return False, msg

            if leverage <= 0:
                return False, "Invalid leverage selected"

            if (
                    (pos_side == PositionSide.LONG and leverage > max_long_leverage)
                    or (pos_side == PositionSide.SHORT and leverage > max_short_leverage)
            ):
                return False, "Invalid leverage selected"

            try:
                self.client.trade.change_leverage(tool, pos_side, leverage)
            except:
                logger.exception(f'Failed to place open order for {tool} due to failure to change leverage')
                return False, "Failed to change leverage"

            pot_loss, _ = self.calculate_position_potential_loss_and_profit(tool, entry_p, stop_p, take_profits,
                                                                            volume)
            # Creating trade and linked position in db
            trade = Trade.create_trade(pos_side.value, self.fresh_account, tool, Decimal((pot_loss / deposit) * 100),
                                       pot_loss,
                                       leverage,
                                       trigger_p,
                                       entry_p,
                                       stop_p, take_profits, move_stop_after, volume, timezone.now())

            success, msg = self._place_primary_order(tool, trigger_p, entry_p, stop_p, take_profits[0], pos_side,
                                                     volume)

            if success:
                logger.success(f'Primary order for {tool} placed successfully')
                self.create_price_listener_in_thread(tool)

                return True, "Primary order placed"
            else:
                logger.error(f'Failed to place primary order for {tool}')
                if trade:
                    trade.delete()
                return False, msg

    def place_stop_loss_order(self, tool: str, stop_p: Decimal, volume: Decimal, pos_side: PositionSide) -> Tuple[
        bool, str]:
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
        try:
            self.client.trade.create_order(order)
            logger.success(f'Placed stop-loss at {stop_p} for volume of {volume}')
            return True, ""
        except Exception as e:
            logger.critical(f'Failed to place stop-loss for {pos_side} {tool} at {stop_p}: {e}')
            return False, str(e)

    def cancel_stop_loss_for_tool(self, tool: str) -> Tuple[bool, str]:
        """
        Cancels the stop loss order for a tool
        :param tool: Tool name
        """
        success, msg, orders = self.get_orders_for_tool(tool)

        if not success:
            logger.error(f'Failed to get orders for tool {tool} for canceling stop-loss order')
            return False, msg

        stop_order = orders.get('stop')
        if not stop_order:
            logger.warning(f'No stop-loss order found for {tool}')
            return False, "No stop order found"

        stop_order_id = stop_order.get('orderId')
        if not stop_order_id:
            logger.warning(f'No stop-loss order ID found for {tool}')
            return False, "No stop order ID found"
        try:
            self.client.trade.cancel_order(stop_order_id, tool)
            logger.success(f'Canceled stop-loss order for {tool}')
            return True, ""
        except Exception as e:
            logger.critical(f'Failed to cancel stop-loss order for {tool}: {stop_order}')
            return False, str(e)

    def cancel_take_profits_for_tool(self, tool: str) -> Tuple[bool, str]:
        """
        Cancels all take profit orders for a trading pair.
        :param tool: The trading pair.
        """
        success, msg, orders = self.get_orders_for_tool(tool)

        if not success:
            logger.error(f'Failed to get orders for {tool} for canceling take-profit orders')
            return False, msg

        take_orders = orders.get('takes')
        if not take_orders:
            logger.warning(f'No take-profit orders found for {tool}')
            return False, "No take profit orders found."

        for take_order in take_orders:
            take_order_id = take_order.get('orderId')
            if not take_order_id:
                logger.warning(f'No take-profit order ID found for {tool}')
                continue

            try:
                self.client.trade.cancel_order(take_order_id, tool)
                logger.success(f'Canceled take-profit order for {tool}')
            except Exception as e:
                logger.critical(f'Failed to cancel take-profit order for {tool}: {take_order}')
                return False, str(e)

        return True, ""

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False,
                                      reason: str = None) -> Tuple[bool, str]:
        """
        Cancels the primary order for a trading pair.
        :param reason: Reason for canceling position.
        :param tool: The trading pair.
        :param save_to_db: Whether to save the cancellation to the database.
        :param only_cancel: Whether to only cancel the order without updating db.
        """

        success, msg, orders = self.get_orders_for_tool(tool)

        if not success:
            logger.error(f'Failed to get orders for {tool} for canceling primary order')
            return False, msg

        entry_order_id = orders['entry']['orderId']

        try:
            self.client.trade.cancel_order(entry_order_id, tool)
        except Exception as e:
            logger.critical(f'Failed to cancel primary order for {tool}')
            return False, str(e)

        if not only_cancel:
            # first() and reverse order IS CRUCIAL, as we only fetch trades by name of tool, and not some unique ID within whole account
            trade = Trade.objects.filter(account=self.fresh_account, tool__name=tool).order_by('-pk').first()
            if save_to_db:
                # For positions closing, cancellation via overhigh/overlow and automatic cancellation of orders when reached take-profit level, their data is being saved into database
                pos = Position.objects.filter(pk=trade.position.pk).first()
                pos.close_position(reason)
            else:
                # For manual cancellation of position, data doesn't go to db
                trade.delete()  # position will be auto deleted, see models.py for this

        self.delete_price_listener(tool)
        return True, ""

    def place_take_profit_orders(self, tool: str, take_profits: List[Decimal], cum_volume: Decimal,
                                 pos_side: PositionSide) -> Tuple[bool, str]:
        """
        Places take profit orders for a trading pair.
        :param tool: The trading pair.
        :param take_profits: List of take profit prices.
        :param cum_volume: Cumulative volume.
        :param pos_side: Position side (LONG/SHORT).
        """

        order_side = Side.SELL if pos_side == "LONG" else Side.BUY
        order_type = OrderType.TAKE_PROFIT_MARKET

        success, dict_with_quantity_precision = self._get_tool_precision_info(tool)

        if not success:
            logger.error(f'Failed to fetch quantity precision for {tool} for placing take-profit orders')
            return False, "Failed to fetch quantity precision"

        quantity_precision = dict_with_quantity_precision['quantityPrecision']

        volumes = mh.calc_take_profits_volumes(cum_volume, quantity_precision, len(take_profits))

        for take_profit, volume in zip(take_profits, volumes):
            order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                          stopPrice=take_profit)
            try:
                self.client.trade.create_order(order)

                logger.success(f'Placed take-profit order for {tool}: at {take_profit} with volume {volume}')
            except Exception as e:
                logger.exception(f'Failed to place take-profit order for {tool}: at {take_profit} with volume {volume}')
                return False, str(e)
        return True, "Successfully placed take profit orders."

    def close_by_market(self, tool: str) -> Tuple[bool, str]:
        trade = Trade.objects.filter(account=self.fresh_account, tool__name=tool).order_by('-pk').first()

        pos = Position.objects.filter(pk=trade.position.pk).first()

        order_side = Side.SELL if pos.side == "LONG" else Side.BUY
        order = Order(symbol=tool, side=order_side, positionSide=pos.side, quantity=pos.max_held_volume)

        try:
            self.client.trade.close_order(order)
            logger.success(f'Closed position for {tool} by market')
            return True, "Closing market order placed successfully"
        except Exception as e:
            logger.critical(f'Failed to close position for {tool} by market order')
            return False, str(e)

    def get_orders_for_tool(self, tool: str) -> Tuple[bool, str, dict[str, Any]]:
        """
        Gets all open orders for a trading pair.
        :param tool: The trading pair.
        :return: dictionary containing entry, take profit, and stop orders.
        """
        try:
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

            return True, "Successfully retrieved orders for tool", {'entry': entry, 'takes': tps, 'stop': stop}
        except Exception as e:
            logger.warning(f'Failed to get orders for {tool}')
            return False, str(e), {}

    def get_current_positions_info(self) -> Tuple[bool, str, List[dict[str, Any]]]:
        """
        Gets information about all current positions.
        :return: List of dictionaries containing position information.
        """
        try:
            positions = self.client.account.get_swap_positions()

            dicts = []

            for position in positions:
                tool_name = position['symbol']
                try:
                    db_pos = self.fresh_account.positions.get(tool__name=tool_name)
                except Position.DoesNotExist as e:
                    logger.warning(
                        f'There is an open position for {tool_name} on server, but it is not in database\n{e}')
                    continue

                trade = db_pos.trade

                d = {
                    'trade_id': trade.pk,
                    'tool': tool_name,
                    'pos_side': position['positionSide'],
                    'leverage': str(position['leverage']),
                    'volume': str(position['availableAmt']),
                    'margin': str(round(Decimal(position['margin']), 3)),
                    'avg_open': str(position['avgPrice']),
                    'current_pnl_risk_reward_ratio':
                        str(mh.floor_to_digits(
                            (Decimal(position['unrealizedProfit']) + Decimal(
                                position['realisedProfit'])) / trade.risk_usd,
                            4)),
                    'realized_pnl': str(mh.floor_to_digits(Decimal(position['realisedProfit']), 4)),
                    'current_pnl':
                        str(mh.floor_to_digits(
                            Decimal(position['unrealizedProfit']) + Decimal(position['realisedProfit']),
                            4)),
                    'open_date': db_pos.start_time,
                    'description': trade.description,
                }

                dicts.append(d)

            return True, "Successfully retrieved current positions", dicts
        except Exception as e:
            logger.warning('Failed to fetch current positions info')
            return False, str(e), []

    def get_pending_positions_info(self) -> List[dict[str, Any]]:
        """
        Gets information about all pending positions.
        :return: List of dictionaries containing pending position information.
        """
        positions = Position.objects.filter(account=self.fresh_account).all()

        dicts = []

        for pos in positions:
            if pos.last_status in ["NEW", "PARTIALLY_FILLED"]:
                d = {
                    'trade_id': pos.trade.pk,
                    'tool': pos.tool.name,
                    'entry_price': str(pos.entry_price),
                    'trigger_price': str(pos.trigger_price),
                    'stop_price': str(pos.stop_price),
                    'take_profit_prices': [str(price) for price in pos.take_profit_prices],
                    'pos_side': pos.side,
                    'leverage': str(pos.leverage),
                    'volume': str(pos.primary_volume),
                    'margin': str(round(Decimal(pos.entry_price * pos.primary_volume / pos.leverage), 3)),
                    'cancel_levels': [str(level) if level is not None else level for level in pos.cancel_levels],
                    'status': pos.last_status
                }

                dicts.append(d)

        return dicts

    def get_open_orders(self, position_id: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        :return: Tuple of stop-loss order dict, and a list of take-profit order dicts
        """
        open_orders = self.client.trade.get_open_orders().get('orders', [])
        if not open_orders:
            return {}, []

        # logger.info(format_dict_for_log(open_orders))

        position_id = int(position_id)

        stop_loss_order = {}
        take_profit_orders = []

        for order in open_orders:
            if order['positionID'] == position_id:
                if order['type'] == 'STOP_MARKET':
                    stop_loss_order = order
                elif order['type'] == 'TAKE_PROFIT_MARKET':
                    take_profit_orders.append(order)

        return stop_loss_order, take_profit_orders

    def get_current_positions(self) -> list[dict[str, Any]]:
        current_positions = self.client.account.get_swap_positions()

        return current_positions

    def get_position_result(self, db_pos: Position) -> tuple[Decimal, Decimal]:
        """
        Based on history orders bound to position via position id calculates its net profit and commission
        :return: Net profit and commission for position
        """
        end_ts = int(time.time()) * 1000 + 5 * 60 * 1000  # Add 5 minutes for proper querying
        start_time_ms = int(db_pos.start_time.timestamp()) * 1000
        start_ts = start_time_ms - 5 * 60 * 1000  # Subtract 5 minutes for proper querying

        history_order = HistoryOrder(symbol=db_pos.tool.name, startTime=start_ts, endTime=end_ts)
        position_id = db_pos.server_position_id

        try:
            orders = self.client.trade.get_orders_history(history_order).get('orders', [])

            logger.info(format_dict_for_log(orders))

            profit = Decimal(0)
            commission = Decimal(0)

            executed_qty = 0

            for order in orders:
                if str(order['positionID']) == position_id:
                    profit_chunk = Decimal(order['profit'])
                    commission_chunk = Decimal(order['commission'])

                    # Don't count entry order volume
                    if order['type'] != 'LIMIT' and order['type'] != 'TRIGGER_LIMIT':
                        executed_qty += Decimal(order['executedQty'])

                    profit += profit_chunk
                    commission += commission_chunk

                    if profit_chunk or commission_chunk:
                        logger.info(
                            f'Found bound order, type: {order['type']}, profit: {Decimal(order['profit'])}, commission: {Decimal(order['commission'])}\n{format_dict_for_log(order)}')

            # print(executed_qty, db_pos.max_held_volume)
            if executed_qty == db_pos.max_held_volume:
                # The commission is always negative
                net_profit = profit + commission

                return net_profit, commission
            else:
                logger.info(f'Orders history is not yet fully processed by BingX side {db_pos.tool.name}')
                return Decimal(0), Decimal(0)
        except:
            logger.exception(f'Failed to get orders history for {db_pos.tool.name}')
            return Decimal(0), Decimal(0)


class ByBitExc(Exchange):
    pass
