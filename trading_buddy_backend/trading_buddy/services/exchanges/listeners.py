import json
import threading
import time
from decimal import Decimal

import websocket
import gzip
import io
import schedule
from django.utils import timezone

from bingX.perpetual.v2.other import Other

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
        print(f'{self.__class__.__name__}: WebSocket connected')

    def on_message(self, ws, message):
        utf8_data = self.decode_data(message)

        if utf8_data == "Ping":  # this is very important , if you receive 'Ping' you need to send 'Pong'
            print(f"{self.__class__.__name__}: {timezone.now()} Ping")
            ws.send("Pong")

        return utf8_data

    def on_error(self, ws, error):
        print(f"{self.__class__.__name__}: {timezone.now()} Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print(
            f'{self.__class__.__name__}: The connection is closed! Status code: {close_status_code}, Close message: {close_msg}')

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
        self.ws_url = "wss://open-api-swap.bingx.com/swap-market"
        self.exchange = exchange


class BingXOrderListener(BingXListener):
    def extend_listen_key_validity(self):
        self.other.extend_listen_key_validity_period(self.listen_key)

        print(f"{self.__class__.__name__}: {timezone.now()} Extended listen key validity: {self.listen_key}")

    def run_scheduler(self):
        print(self.listen_key)
        job = schedule.every(7).minutes.do(self.extend_listen_key_validity)
        self.scheduled_jobs.append(job)

    def __init__(self, manager, exchange):
        super().__init__(exchange)

        self.other = Other(api_key=self.API_KEY, secret_key=self.SECRET_KEY)

        self.manager = manager

        listen_key_response = self.other.generate_listen_key()
        self.listen_key = listen_key_response['listenKey']
        self.ws_url = f"{self.ws_url}?listenKey={self.listen_key}"

        self.scheduled_jobs = []
        self.run_scheduler()

        self.ws = None

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

        print(f"READ TAKES AND STOP:                             {takes}, {stop}")

        print(f"LAST                    STATUS OF           POSITION IS NOW: {ls}")

        # Placing stop-loss
        try:
            self.exchange.place_stop_loss_order(tool, stop, volume, pos_side)
        except Exception as e:
            print(e)

        # Placing take-profits
        print(f"PLACING TAKE PROFITS: {takes}, {volume}")
        try:
            self.exchange.place_take_profit_orders(tool, takes, volume, pos_side)
        except Exception as e:
            print(e)

    def cancel_takes_and_stops(self, tool):
        self.exchange.cancel_stop_loss_for_tool(tool)
        self.exchange.cancel_take_profits_for_tool(tool)

    def on_fill_primary_order(self, tool, avg_price, volume, new_commission):
        print(f"{self.__class__.__name__}: ORDER IS FILLED")

        # It seems like because program use multi-threaded, runtime_manager can't finish writing data into json in
        # add_position() function when order is immediately filled up after its placing, so we've gotta to pause a
        # bit this function so rm would finish its business
        time.sleep(3)

        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        left_volume_to_fill, commission, last_status, fill_history = pos.primary_volume - pos.current_volume, pos.commission_usd, pos.last_status, pos.fill_history

        if last_status == "PARTIALLY_FILLED":
            # If order was previously partially filled - call partial fill func once again
            self.on_partial_fill_primary_order(tool, avg_price, volume, new_commission)
        else:

            print(f"LEFT VOLUME TO FILL: {left_volume_to_fill}")

            fill_history.append([avg_price, volume])

            pos.entry_price = avg_price  # ABSOLUTELY CRUCIAL FOR MOVING STOP-LOSS TO BREAK-EVEN
            pos.last_status = "FILLED"
            pos.current_volume = volume
            pos.commission_usd = commission + new_commission
            pos.start_time = timezone.now()
            pos.fill_history = fill_history
            pos.save()

            self.place_takes_and_stops(tool, volume)

    def on_partial_fill_primary_order(self, tool, avg_price, volume, new_commission):
        print(f"{self.__class__.__name__}: ORDER IS PARTIALLY FILLED")

        # It seems like because program is multi-threaded, runtime_manager can't finish writing data into json in
        # add_position() function when order is immediately filled up after its placing, so we got to pause a
        # bit this function so rm would finish its business
        time.sleep(3)

        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        left_volume_to_fill, current_volume, commission, last_status, fill_history = pos.primary_volume - pos.current_volume, pos.current_volume, pos.commission_usd, pos.last_status, pos.fill_history

        current_volume += volume
        left_volume_to_fill -= volume
        fill_history.append([avg_price, current_volume])

        pos.current_volume = current_volume
        pos.fill_history = fill_history

        if last_status == "NEW":
            # Set start_time only if it wasn't set yet
            pos.start_time = timezone.now()

            self.place_takes_and_stops(tool, volume)

        elif last_status == "PARTIALLY_FILLED":
            self.cancel_takes_and_stops(tool)

            self.place_takes_and_stops(tool, current_volume)

        pos.commission_usd = commission + new_commission
        pos.last_status = "PARTIALLY_FILLED" if left_volume_to_fill != 0 else "FILLED"
        pos.save()

        # Stopping price listener
        self.exchange.delete_price_listener(tool)

    def on_stop(self, tool, new_pnl, new_commission):
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        commission, pnl = pos.commission_usd, pos.pnl_usd

        pos.pnl_usd = pnl + new_pnl
        pos.commission_usd = commission + new_commission
        pos.last_status = "STOP"
        pos.save()

        pos.close_position()

    def on_take_profit(self, tool, volume, new_pnl, new_commission, status):
        print(f"{self.__class__.__name__}: FILLING TAKE_PROFIT")

        # Cancel previous stop-loss and place new if stop-loss wasn't moved yet
        pos = Position.objects.filter(account=self.fresh_account, tool__name=tool).first()
        breakeven, pnl, commission, last_status = pos.breakeven, pos.pnl_usd, pos.commission_usd, pos.last_status

        pos.pnl_usd = pnl + new_pnl
        pos.commission_usd = commission + new_commission
        pos.last_status = "TAKE-PROFIT"

        if last_status == "PARTIALLY_FILLED":
            self.exchange.cancel_primary_order_for_tool(tool, only_cancel=True)

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
                    self.exchange.cancel_stop_loss_for_tool(tool)

                    entry_p = pos.entry_price
                    print(f"PLACING STOP LOSS ON {entry_p}")

                    self.exchange.place_stop_loss_order(tool, entry_p, volume_for_stop_loss, pos_side)
                    pos.move_stop_after -= 1
                    pos.breakeven = True
                    pos.save()
        else:
            pos.save()

    def on_message(self, ws, message):
        utf8_data = super().on_message(ws, message)

        schedule.run_pending()  # Extending listen key validity

        if utf8_data != "Ping":
            if "ORDER_TRADE_UPDATE" in utf8_data:
                print(f"{self.__class__.__name__}: ORDER UPDATE")

                tool, order_type, volume, avg_price, status, pnl, commission = self.extract_info_from_utf_data(
                    utf8_data)

                print(f"DATA FOR NEW ORDER: {utf8_data}")

                if order_type == "TRIGGER_LIMIT" or order_type == "LIMIT":
                    if status == "FILLED":
                        self.on_fill_primary_order(tool, avg_price, volume, commission)

                    elif status == "PARTIALLY_FILLED":
                        self.on_partial_fill_primary_order(tool, avg_price, volume, commission)

                elif order_type == "STOP_MARKET":  # CHECK IF THIS WORKS IN FUTURE
                    if status == "PARTIALLY_FILLED" or status == "FILLED":
                        self.on_stop(tool, pnl, commission)

                elif order_type == "TAKE_PROFIT_MARKET":
                    if status == "PARTIALLY_FILLED" or status == "FILLED":
                        self.on_take_profit(tool, volume, pnl, commission, status)

    def on_close(self, ws, close_status_code, close_msg):
        super().on_close(ws, close_status_code, close_msg)

        print("BingXOrderListener: Deleting listener...")

        for job in self.scheduled_jobs:
            schedule.cancel_job(job)
        self.scheduled_jobs = []

        self.manager.on_close_listener()

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
        self.exchange = exchange
        self.order_listener = BingXOrderListener(self, self.exchange)
        self.order_listener.listen_for_events()

    def on_close_listener(self):
        print("OrderListenerManager: Restarting BingX Order Listener...")

        self.order_listener = BingXOrderListener(self, self.exchange)
        self.order_listener.listen_for_events()


class BingXPriceListener(BingXListener):
    def __init__(self, tool, exchange):
        super().__init__(exchange)

        self.tool = tool

        self.CHANNEL = {"id": "24dd0e35-56a4-4f7a-af8a-394c7060909c", "reqType": "sub", "dataType": f"{tool}@lastPrice"}

    def check_price_for_order_cancellation(self, price):
        pos = self.fresh_account.positions.filter(tool__name=self.tool).first()

        # HERE IS WHY ORDER OF CANCEL LEVELS IS CRUCIAL
        over_and_take, pos_side = pos.cancel_levels, pos.side
        print("PRICE LISTENER ALIVE")

        try:
            over, take = over_and_take

            if pos_side == "LONG":
                if (over is not None and price <= over) or (take is not None and price >= take):
                    print(f"LONG: over: {over}, take: {take}, price: {price}")
                    self.exchange.cancel_primary_order_for_tool(self.tool, True,
                                                                reason="Overlow or price got too close to take-profit")
            else:
                if (over is not None and price >= over) or (take is not None and price <= take):
                    print(f"SHORT: over: {over}, take: {take}, price: {price}")
                    self.exchange.cancel_primary_order_for_tool(self.tool, True,
                                                                reason="Overbuy or price got too close to take-profit")

        except Exception as e:
            # print(f"{__class__.__name__}, {self.tool}: Cancelation levels for {self.tool} not specified: {e}")
            pass

    def on_open(self, ws):
        super().on_open(ws)
        sub_str = json.dumps(self.CHANNEL)
        ws.send(sub_str)
        # (f"{self.__class__.__name__}, {self.tool}: Subscribed to :", subStr)

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
