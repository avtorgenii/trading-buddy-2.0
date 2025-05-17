from decimal import Decimal
from typing import List, Dict, Tuple, Optional, Any, Union
import threading

from django.utils import timezone

from bingX.perpetual.v2 import PerpetualV2
from bingX.perpetual.v2.types import (Order, OrderType, Side, PositionSide, MarginType)
from bingX.exceptions import ClientError
from trading_buddy_backend.trading_buddy.models import Account, User, Position, Trade, Tool

from trading_buddy_backend.trading_buddy.services.exchanges import math_helper as mh


class Exchange:
    """
    Base Exchange class that defines the interface for all exchanges.
    Implements a per-user, per-exchange type singleton pattern.
    """

    #  {user_identifier: {exchange_name: exchange_instance}}
    _instances_by_user: Dict[Any, Dict[str, 'Exchange']] = {}
    _lock = threading.Lock()  # Lock for thread-safe access to _instances_by_user

    # This class attribute must be defined in subclasses
    account_name: str = "BASE_EXCHANGE"

    def __new__(cls, user_identifier: User, *args, **kwargs):
        """
        Controls the creation of instances, ensuring only one instance exists
        per user for each specific subclass of Exchange.
        """
        if cls.account_name == "BASE_EXCHANGE":
            raise TypeError("Cannot instantiate base Exchange class directly. Use a subclass.")

        if not user_identifier:
            raise ValueError("user_identifier must be provided to instantiate an Exchange client.")

        with cls._lock:
            # Get the dictionary of exchanges for this user, or create it if it doesn't exist
            instances_for_user = cls._instances_by_user.setdefault(user_identifier, {})

            # Check if an instance of this specific exchange type already exists for this user
            if cls.account_name not in instances_for_user:
                instance = super().__new__(cls)
                # Store the newly created instance in the dictionary for this user and exchange type
                instances_for_user[cls.account_name] = instance
                # Indicate that __init__ should be called on this new instance
                instance._initialized = False  # Use a flag to manage initialization in __init__
            else:
                # If an instance already exists, retrieve it
                instance = instances_for_user[cls.account_name]
                # Indicate that __init__ should NOT be fully re-run if it has an init guard
                instance._initialized = True  # Mark as already initialized (for __init__ check)

            # Return the instance (either newly created or existing)
            return instance

    def __init__(self, user: User, *args, **kwargs):
        """
        Initializes the instance. This method is called *after* __new__.
        It is only fully executed the first time an instance for a user/exchange is created.
        """
        # This check ensures that the main initialization logic runs only once
        # for a given instance (i.e., the first time __new__ created it).
        if self._initialized:
            # If _initialized is True, it means __new__ returned an existing instance,
            # so skip the initialization logic.
            return

        print(f"Initializing {self.account_name} client for user: {user}")

        # Store the user identifier with the instance if needed
        self.user = user
        self.account = Account.objects.filter(user=user).first()

        self.API_KEY = self.account.api_key
        self.SECRET_KEY = self.account.secret_key

        # Mark the instance as fully initialized
        self._initialized = True

    def get_account_details(self) -> Tuple[float, float, float, float]:
        raise NotImplementedError("Method not implemented")

    def get_max_leverage(self, tool: str) -> Tuple[float, float]:
        raise NotImplementedError("Method not implemented")

    def calc_position_volume_and_margin(self, tool: str, entry_p: float, stop_p: float, leverage: float) -> Tuple[
        float, float]:
        raise NotImplementedError("Method not implemented")

    def place_open_order(self, tool: str, trigger_p: float, entry_p: float, stop_p: float, take_profits: List[float],
                         move_stop_after: int, leverage: float, volume: float) -> str:
        raise NotImplementedError("Method not implemented")

    def place_stop_loss_order(self, tool: str, stop_p: float, volume: float, pos_side: PositionSide) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_stop_loss_for_tool(self, tool: str) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_take_profits_for_tool(self, tool: str) -> None:
        raise NotImplementedError("Method not implemented")

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False) -> None:
        raise NotImplementedError("Method not implemented")

    def place_take_profit_orders(self, tool: str, take_profits: List[float], cum_volume: float,
                                 pos_side: PositionSide) -> None:
        raise NotImplementedError("Method not implemented")

    def get_orders_for_tool(self, tool: str) -> Dict[str, Any]:
        raise NotImplementedError("Method not implemented")

    def get_current_positions_info(self) -> List[Dict[str, Any]]:
        raise NotImplementedError("Method not implemented")


class BingXExc(Exchange):
    """
    BingX Exchange implementation as a Singleton class.
    Tool format: "<name>-USDT"
    """
    account_name = "BingX"

    def __init__(self, user: User, *args, **kwargs):
        """
        Initialize the BingX exchange with API credentials.
        """
        super().__init__(user, *args, **kwargs)

        self.client = PerpetualV2(api_key=self.API_KEY, secret_key=self.SECRET_KEY)

        # Listeners for cancel prices of tools
        self.listeners_threads = []

    def get_deposit_and_risk(self) -> Tuple[Decimal, Decimal]:
        """
        Returns the deposit and risk % values from the database.
        :return: A tuple containing deposit and risk %.
        """
        return self.user.deposit, self.user.risk_percent

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

    def get_max_leverage(self, tool: str) -> Tuple[Decimal, Decimal]:
        """
        Returns the maximum leverage for a trading pair.
        :param tool: The trading pair.
        :return: A tuple containing the maximum long leverage and maximum short leverage.
        """
        info = self.client.trade.get_leverage(tool)
        return info["maxLongLeverage"], info["maxShortLeverage"]

    def calc_position_volume_and_margin(self, tool: str, entry_p: Decimal, stop_p: Decimal, leverage: Decimal) -> Tuple[
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
        Switches the margin mode to cross for a trading pair.
        :param tool: The trading pair.
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

        # If trigger price is not specified, system treats order as limit order
        order_type = OrderType.TRIGGER_LIMIT if trigger_p != 0 else OrderType.LIMIT

        order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                      price=entry_p, stopPrice=trigger_p)
        order_response = self.client.trade.create_order(order)

        return order_response['order']['orderId']

    def place_open_order(self, tool: str, trigger_p: Decimal, entry_p: Decimal, stop_p: Decimal,
                         take_profits: List[Decimal], move_stop_after: int, leverage: Decimal,
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
        self._switch_margin_mode_to_cross(tool)

        pos_side = PositionSide.LONG if entry_p > stop_p else PositionSide.SHORT

        self.client.trade.change_leverage(tool, pos_side, leverage)

        try:
            self._place_primary_order(tool, trigger_p, entry_p, stop_p, pos_side, volume)

            pot_loss, _ = self.calculate_position_potential_loss_and_profit(tool, entry_p, stop_p, take_profits,
                                                                            volume)

            print(f"POTENTIAL LOSS OF A TRADE: {pot_loss} \n WITH VOLUME: {volume}")

            tool_obj = Tool.objects.get(name=tool)

            # Creating trade in db
            deposit, risk = self.get_deposit_and_risk()

            trade = Trade.objects.create(side=pos_side, tool=tool_obj, risk_percent=risk, risk_usd=deposit * risk / 100)

            # Adding primary order info to db
            Position.objects.create(tool=tool_obj, side=pos_side, leverage=leverage, trigger_price=trigger_p,
                                    entry_price=entry_p,
                                    stop_price=stop_p, take_profit_prices=take_profits, cancel_levels=[take_profits[0]],
                                    move_stop_after=move_stop_after, primary_volume=volume, current_volume=0,
                                    account=self.user.accounts.get(name=self.account_name), trade=trade)

            return "Primary order placed"
        except ClientError as e:
            if e.error_message == "Insufficient margin":
                return "Please enter volume manually"

            else:
                return "Volume is too small"

    def place_stop_loss_order(self, tool: str, stop_p: Decimal, volume: Decimal, pos_side: str) -> None:
        """
        Places a stop loss order.
        :param tool: The trading pair.
        :param stop_p: Stop loss price.
        :param volume: Trading volume.
        :param pos_side: Position side (LONG/SHORT).
        """
        order_side = Side.SELL if pos_side == "LONG" else Side.BUY
        order_type = OrderType.STOP_MARKET

        order = Order(symbol=tool, side=order_side, positionSide=pos_side, quantity=volume, type=order_type,
                      stopPrice=stop_p)
        self.client.trade.create_order(order)

        print(f"PLACED SL: price: {stop_p}, volume: {volume}")

    def cancel_stop_loss_for_tool(self, tool: str) -> None:
        """
        Cancels the stop loss order for a trading pair.
        :param tool: The trading pair.
        """
        orders = self.get_orders_for_tool(tool)

        print(orders)

        stop_order_id = orders['stop']['orderId']

        resp = self.client.trade.cancel_order(stop_order_id, tool)

        print(f"STOP ORDER CANCELLATION RESPONSE: {resp}")

    def cancel_take_profits_for_tool(self, tool: str) -> None:
        """
        Cancels all take profit orders for a trading pair.
        :param tool: The trading pair.
        """
        orders = self.get_orders_for_tool(tool)

        print(orders)

        take_orders = orders['takes']

        for take_order in take_orders:
            take_order_id = take_order['orderId']

            resp = self.client.trade.cancel_order(take_order_id, tool)

            print(f"TAKE ORDER CANCELLATION RESPONSE: {resp}")

    def cancel_primary_order_for_tool(self, tool: str, save_to_db: bool = False, only_cancel: bool = False) -> None:
        """
        Cancels the primary order for a trading pair.
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
            tool_obj = Tool.objects.get(name=tool)
            trade = Trade.objects.filter(account=self.account, tool=tool_obj).last()
            if save_to_db:
                # For positions closing, cancellation via overhigh/overlow and automatic cancellation of orders when reached take-profit level, their data is being saved into database
                pos = trade.position

                trade.volume = pos.volume
                trade.pnl_usd = pos.pnl_usd
                trade.commission_usd = pos.commission_usd
                trade.start_time = pos.start_time
                trade.end_time = timezone.now()

                trade.save()
                pos.delete()

                # TODO delete price listener
            else:
                # For manual cancellation of position, data doesn't go to db
                trade.delete()  # position will be auto deleted, see models.py for this
                # TODO delete price listener

    def place_take_profit_orders(self, tool: str, take_profits: List[Decimal], cum_volume: Decimal,
                                 pos_side: str) -> None:
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

    def get_pending_positions_info(self) -> List[Dict[str, Any]]:
        """
        Gets information about all pending positions.
        :return: List of dictionaries containing pending position information.
        """
        positions = Position.objects.filter(account=self.account).all()

        print(positions)

        dicts = []

        for pos in positions:
            if pos.last_status == "NEW":
                d = {
                    'tool': pos.tool,
                    'entry_price': pos.entry_price,
                    'pos_side': pos.pos_side,
                    'leverage': pos.leverage,
                    'volume': pos.primary_volume,
                    'margin': pos.entry_price * pos.primary_volume / pos.leverage,
                    'trigger_price': pos.trigger_p
                }

                dicts.append(d)

        return dicts
