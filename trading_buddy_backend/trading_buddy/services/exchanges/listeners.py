import json
import time
from decimal import Decimal

import websocket
import gzip
import io
import schedule
from django.db import connection, OperationalError
from django.utils import timezone

from bingX.perpetual.v2.other import Other
from loguru import logger

from ...models import User, Account, Position


def format_dict_for_log(dict_data: dict) -> str:
    return json.dumps(dict_data, indent=2).replace("{", '').replace("}", '')


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

        self.consecutive_errors = 0

        self.ws_url = "wss://open-api-swap.bingx.com/swap-market"
        self.exchange = exchange


class BingXPriceListener(BingXListener):
    def __init__(self, tool, exchange):
        self.tool = tool
        self.CHANNEL = {"id": "24dd0e35-56a4-4f7a-af8a-394c7060909c", "reqType": "sub", "dataType": f"{tool}@lastPrice"}

        super().__init__(exchange)
        self.logger = self.logger.bind(class_name=self.__class__.__name__)

    def check_price_for_order_cancellation(self, price):
        try:
            # Always close stale connections before attempting work,
            # because Django doesn't automatically update connections for threads - one thread - one connection
            connection.close()

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
                self.logger.exception(f'Tried to check price for order cancelling: {e}')

            self.consecutive_errors = 0

        except OperationalError as e:
            self.consecutive_errors += 1

            if self.consecutive_errors % 60 == 1:  # Log every minute
                logger.warning(f'DB unavailable ({self.consecutive_errors}s): {e}')

        except Exception as e:
            logger.exception(f'Uncaught exception: {e}')
            self.consecutive_errors = 0

        time.sleep(5)



    def on_open(self, ws):
        super().on_open(ws)
        sub_str = json.dumps(self.CHANNEL)
        ws.send(sub_str)

    def on_message(self, ws, message):
        utf8_data = super().on_message(ws, message)

        if utf8_data and utf8_data != "Ping":
            dict_data = json.loads(utf8_data)
            # self.logger.info(f"Received data: {format_dict_for_log(dict_data)}")

            try:
                price = Decimal(dict_data["data"]["c"])

                if price is not None:
                    self.check_price_for_order_cancellation(price)
            except:
                self.logger.debug(f'Failed to retrieve price data for {self.tool} from dict data sent by BingX')

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
