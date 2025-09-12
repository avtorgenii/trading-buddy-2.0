import json
import time
from decimal import Decimal

import websocket
import gzip
import io
import schedule
from django.utils import timezone

from bingX.perpetual.v2.other import Other
from loguru import logger

from ...models import User, Account, Position


class Listener:
    def __init__(self, user: User, account: Account):
        self._user = user
        self._account = account

        # Thanks to the logic where you cannot update account data (API stuff), below variables initializing once is perfectly okay
        self.API_KEY = self.fresh_account.api_key
        self.SECRET_KEY = self.fresh_account.secret_key

        self.ws = None
        self.ws_url = None

        self.logger = logger.bind(class_name=self.__class__.__name__)

    @property
    def fresh_account(self):
        return Account.objects.get(pk=self._account.pk)

    @property
    def fresh_user(self):
        return User.objects.get(pk=self._user.pk)

    def decode_data(self, message):
        compressed_data = gzip.GzipFile(fileobj=io.BytesIO(message), mode='rb')
        decompressed_data = compressed_data.read()

        return decompressed_data.decode('utf-8')

    def on_open(self, ws):
        self.logger.info('WebSocket connected')

    def on_message(self, ws, message):
        utf8_data = self.decode_data(message)

        if utf8_data == "Ping":  # this is very important, if you receive 'Ping' you need to send 'Pong'
            # self.logger.debug('Pong')
            ws.send("Pong")

        return utf8_data

    def on_error(self, ws, error):
        self.logger.error(error)

    def on_close(self, ws, close_status_code, close_msg):
        self.logger.warning(
            f"Listener's connection was closed. Status code: {close_status_code}. Close message: {close_msg}")

    def listen_for_events(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )

        self.ws.run_forever()

    def stop_listening(self):
        self.ws.close()


class BingXListener(Listener):
    def __init__(self, exchange):
        super().__init__(exchange.fresh_user, exchange.fresh_account)
        self.logger = self.logger.bind(class_name=self.__class__.__name__)

        self.ws_url = "wss://open-api-swap.bingx.com/swap-market"
        self.exchange = exchange


class BingXOrderListener(BingXListener):
    def extend_listen_key_validity(self):
        self.other.extend_listen_key_validity_period(self.listen_key)

        self.logger.info(f'Extended listen key validity: {self.listen_key}')

    def run_scheduler(self):
        job = schedule.every(7).minutes.do(self.extend_listen_key_validity)
        self.scheduled_jobs.append(job)

    def __init__(self, exchange):
        super().__init__(exchange)
        self.logger = self.logger.bind(class_name=self.__class__.__name__)

        try:
            self.other = Other(api_key=self.API_KEY, secret_key=self.SECRET_KEY)

            listen_key_response = self.other.generate_listen_key()
            self.listen_key = listen_key_response['listenKey']
            self.ws_url = f"{self.ws_url}?listenKey={self.listen_key}"

            self.scheduled_jobs = []
            self.run_scheduler()

            self.ws = None
        except:
            self.logger.exception(f'Failed to generate listen key')
            raise

    def extract_info_from_utf_data(self, data):
        dict_data = json.loads(data)

        order = dict_data["o"]

        tool = order["s"]
        order_type = order["o"]
        volume = Decimal(order["q"])
        avg_price = Decimal(order["ap"])
        status = order["X"]
        pnl = Decimal(order["rp"])
        commission = Decimal(order["n"])

        return tool, order_type, volume, avg_price, status, pnl, commission

    def place_takes_and_stops(self, tool, volume):
        # Stopping price listener
        self.exchange.delete_price_listener(tool)

        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        pos_side, takes, stop, ls = pos.side, pos.take_profit_prices, pos.stop_price, pos.last_status

        self.logger.info(f"Last status of position is now: {ls}")

        # Placing stop-loss
        stop_success, stop_msg = self.exchange.place_stop_loss_order(tool, stop, volume, pos_side)
        if not stop_success:
            self.logger.critical(f'Failed to place stop-loss order for {tool}')

        # Placing take-profits
        takes_success, takes_msg = self.exchange.place_take_profit_orders(tool, takes, volume, pos_side)
        if not takes_success:
            self.logger.critical(f'Failed to place take-profit orders for {tool}')

    def cancel_takes_and_stops(self, tool):
        stop_success, stop_msg = self.exchange.cancel_stop_loss_for_tool(tool)
        if not stop_success:
            self.logger.critical(f'Failed to cancel stop-loss order for {tool}')

        takes_success, takes_msg = self.exchange.cancel_take_profits_for_tool(tool)
        if not takes_success:
            self.logger.critical(f'Failed to cancel take-profit orders for {tool}')

    def on_fill_primary_order(self, tool, avg_price, volume, new_commission):
        self.logger.success(f'Primary order for {tool} is fully filled')

        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        left_volume_to_fill, last_status, fill_history = pos.primary_volume - pos.current_volume, pos.last_status, pos.fill_history

        if last_status == "PARTIALLY_FILLED":
            # If order was previously partially filled - call partial fill func once again
            self.on_partial_fill_primary_order(tool, avg_price, volume, new_commission)
        else:
            self.logger.info(f'Left volume to fill for {tool}: {left_volume_to_fill}')

            fill_history.append([avg_price, volume])

            pos.entry_price = avg_price  # ABSOLUTELY CRUCIAL FOR MOVING STOP-LOSS TO BREAK-EVEN
            pos.last_status = "FILLED"
            pos.current_volume = volume
            pos.commission_usd += new_commission
            pos.start_time = timezone.now()
            pos.fill_history = fill_history
            pos.save()

            self.place_takes_and_stops(tool, volume)

    def on_partial_fill_primary_order(self, tool, avg_price, volume, new_commission):
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        left_volume_to_fill, current_volume, commission, last_status, fill_history = pos.primary_volume - pos.current_volume, pos.current_volume, pos.commission_usd, pos.last_status, pos.fill_history

        current_volume += volume
        left_volume_to_fill -= volume
        fill_history.append([avg_price, current_volume])

        pos.current_volume = current_volume
        pos.fill_history = fill_history

        if last_status == "NEW":
            self.logger.warning(f'Primary order for {tool} is partially filled')
            # Set start_time only if it wasn't set yet
            pos.start_time = timezone.now()

            self.place_takes_and_stops(tool, volume)

        elif last_status == "PARTIALLY_FILLED":
            self.logger.warning(f'Primary order for {tool} is fully filled')
            self.cancel_takes_and_stops(tool)

            self.place_takes_and_stops(tool, current_volume)

        pos.commission_usd = commission + new_commission
        pos.last_status = "PARTIALLY_FILLED" if left_volume_to_fill != 0 else "FILLED"
        pos.save()

        # Stopping price listener
        self.exchange.delete_price_listener(tool)

    def on_stop(self, tool, new_pnl, new_commission):
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()

        pos.pnl_usd += new_pnl
        pos.commission_usd += new_commission
        pos.last_status = "STOP"
        pos.save()

        pos.close_position()

    def on_take_profit(self, tool, volume, new_pnl, new_commission):
        # Cancel previous stop-loss and place new if stop-loss wasn't moved yet
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        breakeven, last_status = pos.breakeven, pos.last_status

        pos.pnl_usd += new_pnl
        pos.commission_usd += new_commission

        # If last status of entry order was partially_filled, and we already reached take-profit, cancel primary order
        if last_status == "PARTIALLY_FILLED":
            success, msg = self.exchange.cancel_primary_order_for_tool(tool, only_cancel=True)
            if not success:
                self.logger.critical(
                    f"Failed to cancel primary order for partially filled position which reached take-profit!")

        if not breakeven:
            # Decreasing volume for new stop-loss as take-profit already fixed some volume of position
            volume_for_stop_loss = pos.current_volume - volume
            pos.current_volume = volume_for_stop_loss

            # If it was the last take
            if volume_for_stop_loss == 0:
                pos.close_position()
            else:
                # Moving stop-loss to breakeven
                pos_side, move_stop_after = pos.side, pos.move_stop_after

                if move_stop_after == 1:  # decremented below
                    success, msg = self.exchange.cancel_stop_loss_for_tool(tool)

                    if not success:
                        self.logger.critical(f"Failed to cancel stop loss while moving it to breakeven")

                    entry_p = pos.entry_price

                    success, msg = self.exchange.place_stop_loss_order(tool, entry_p, volume_for_stop_loss, pos_side)

                    if not success:
                        self.logger.critical("Failed to place stop loss while moving it to breakeven")

                    pos.move_stop_after -= 1
                    pos.breakeven = True
                    pos.save()
        else:
            pos.save()

    def on_close_by_market(self, tool, volume, new_pnl, new_commission, status):
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()

        pos.pnl_usd += new_pnl
        pos.commission_usd += new_commission

        pos.save()
        pos.close_position()

    def on_message(self, ws, message):
        utf8_data = super().on_message(ws, message)

        schedule.run_pending()  # Extending listen key validity

        if utf8_data != "Ping":
            if "ORDER_TRADE_UPDATE" in utf8_data:
                tool, order_type, volume, avg_price, status, pnl, commission = self.extract_info_from_utf_data(
                    utf8_data)

                # Doesn't work due to curly braces of dict
                # self.logger.info(f'Data for new order: {utf8_data}')

                if order_type == "TRIGGER_LIMIT" or order_type == "LIMIT":  # entry
                    if status == "FILLED":
                        self.on_fill_primary_order(tool, avg_price, volume, commission)

                    elif status == "PARTIALLY_FILLED":
                        self.on_partial_fill_primary_order(tool, avg_price, volume, commission)

                # CHECK IF THIS WORKS IN FUTURE
                elif order_type == "STOP_MARKET":  # stop-loss
                    if status == "PARTIALLY_FILLED" or status == "FILLED":
                        self.on_stop(tool, pnl, commission)

                elif order_type == "TAKE_PROFIT_MARKET":  # take-profit
                    if status == "PARTIALLY_FILLED" or status == "FILLED":
                        self.on_take_profit(tool, volume, pnl, commission)

                elif order_type == "MARKET":  # closing position by market
                    if status == "PARTIALLY_FILLED" or status == "FILLED":
                        self.on_close_by_market(tool, volume, pnl, commission, status)

    def on_close(self, ws, close_status_code, close_msg):
        super().on_close(ws, close_status_code, close_msg)

        self.stop_listening()

        self.logger.error('Deleting listener...')

        for job in self.scheduled_jobs:
            schedule.cancel_job(job)
        self.scheduled_jobs = []

    def listen_for_events(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


class BingXOrderListenerManager:
    """
    Needed for automatic restart of Order Listener
    """

    def __init__(self, exchange):
        self.logger = logger.bind(class_name=self.__class__.__name__)

        self.exchange = exchange
        self.order_listener = None  # Initialize as None

    def on_close_listener(self):
        self.logger.info("The listener has closed. It will be restarted by the manager's loop")

    def run(self):
        """
        A persistent loop to run and restart the listener.
        This should be the main entry point for the manager.
        """
        while True:
            try:
                self.logger.info('Starting BingX Order Listener')
                self.order_listener = BingXOrderListener(self.exchange)
                self.order_listener.listen_for_events()  # This is a blocking call. It will run until the connection closes.

            except Exception as e:
                self.logger.exception('Connection closed for last BingX Order Listener')

            # When listen_for_events() returns (due to on_close), the code continues here.
            self.logger.info('BingX Order Listener stopped. Restarting in 2 seconds')
            time.sleep(2)


class BingXPriceListener(BingXListener):
    def __init__(self, tool, exchange):
        super().__init__(exchange)
        self.logger = self.logger.bind(class_name=self.__class__.__name__)

        self.tool = tool

        self.CHANNEL = {"id": "24dd0e35-56a4-4f7a-af8a-394c7060909c", "reqType": "sub", "dataType": f"{tool}@lastPrice"}

    def check_price_for_order_cancellation(self, price):
        pos = self.fresh_account.positions.filter(tool__name=self.tool).first()

        # HERE IS WHY ORDER OF CANCEL LEVELS IS CRUCIAL
        over_and_take, pos_side = pos.cancel_levels, pos.side

        try:
            over, take = over_and_take

            if pos_side == "LONG":
                if (over is not None and price <= over) or (take is not None and price >= take):
                    self.exchange.cancel_primary_order_for_tool(self.tool, True,
                                                                reason="Оверлой или цена подошла слишком близко к тейку")
            else:
                if (over is not None and price >= over) or (take is not None and price <= take):
                    self.exchange.cancel_primary_order_for_tool(self.tool, True,
                                                                reason="Овербай или цена подошла слишком близко к тейку")

        except Exception as e:
            self.logger.debug('Tried to check price for order cancelling')
            pass

    def on_open(self, ws):
        super().on_open(ws)
        sub_str = json.dumps(self.CHANNEL)
        ws.send(sub_str)

    def on_message(self, ws, message):
        utf8_data = super().on_message(ws, message)

        if utf8_data and utf8_data != "Ping":
            dict_data = json.loads(utf8_data)

            price = Decimal(dict_data["data"]["c"])

            if price is not None:
                self.check_price_for_order_cancellation(price)

    def listen_for_events(self):
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
        )
        self.ws.run_forever()


"""DEBUG"""
if __name__ == "__main__":
    # Short
    # be.place_open_order("OP-USDT", 1.8307, 1.8, 1.87, [1.8302, 1.83], 1)
    # Long
    # res = be.place_open_order("OP-USDT", 1.818, 1.8146, 1.7776, [1.8348, 1.85], 1, 50, 1.5)
    # print(res)
    # listener = OrderListener()
    # listener.listen_for_events()
    # listener = PriceListener("OP-USDT")
    # listener.listen_for_events()

    pass
