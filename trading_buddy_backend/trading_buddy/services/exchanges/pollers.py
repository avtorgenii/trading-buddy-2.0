import json
import time

from schedule import Scheduler

from decimal import Decimal
from ...models import User, Account, Position
from loguru import logger

from threading import Thread

from .exchanges import BingXExc, ByBitExc

exc_map = {
    "BingX": BingXExc,
    # "ByBit": ByBitExc
}


def format_dict_for_log(dict_data: dict) -> str:
    return json.dumps(dict_data, indent=2).replace("{", '').replace("}", '')


class OrderPoller:
    def __init__(self, interval_seconds: int = 5):
        self.scheduler = Scheduler()
        self.scheduler.every(interval_seconds).seconds.do(self.poll_accounts_for_order_statuses)

        self.logger = logger.bind(class_name=self.__class__.__name__)

    def run(self):
        # Blocking call
        while True:
            self.scheduler.run_pending()
            time.sleep(1)

    def poll_accounts_for_order_statuses(self):
        accounts = Account.objects.all()

        self.logger.info('Starting polling accounts...')

        for account in accounts:
            exc = exc_map[account.exchange](account)

            open_orders = exc.get_open_orders()

            self.logger.info(format_dict_for_log(open_orders))

    ##### ORDER MANAGEMENT STUFF #####
    def place_takes_and_stops(self, account: Account, tool: str, volume: Decimal):
        pass

    def cancel_takes_and_stops(self, account: Account, tool: str):
        pass

    def on_fill_primary_order(self, account: Account, tool: str, avg_price: Decimal, volume: Decimal,
                              new_commission: Decimal):
        pass

    def on_partial_fill_primary_order(self, account: Account, tool: str, avg_price: Decimal, volume: Decimal,
                                      new_commission: Decimal):
        pass

    def on_stop_loss(self, account: Account, tool: str, new_pnl: Decimal, new_commission: Decimal):
        pass

    def on_take_profit(self, account: Account, tool: str, new_pnl: Decimal, new_commission: Decimal):
        pass

    def on_close_by_market(self, account: Account, tool: str, volume: Decimal, new_pnl: Decimal,
                           new_commission: Decimal, status: str):
        pass


def init_poller() -> OrderPoller:
    """
    Starts OrderPoller in separate thread
    """
    poller = OrderPoller()
    poller_thread = Thread(target=poller.run, daemon=True)
    poller_thread.start()
    return poller
