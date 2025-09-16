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


def format_dict_for_log(dict_data: dict | list) -> str:
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

    # TODO: finish for all possible cases and refactor by moving code to functions below
    def check_position_statuses_for_account(self, account: Account):
        exc = exc_map[account.exchange](account)

        open_orders_server = exc.get_open_orders().get('orders', [])
        current_positions_server = exc.get_current_positions()

        current_positions_db = Position.objects.filter(account=account)

        self.logger.info(format_dict_for_log(open_orders_server))
        self.logger.info(format_dict_for_log(current_positions_server))

        for db_pos in current_positions_db:
            pos_vanished_from_server = True
            for server_pos in current_positions_server:
                # One position per tool as in rules of usage
                if db_pos.tool.name == server_pos['symbol']:
                    # If position was just filled -
                    # 1. Set its id in db and current volume
                    # 2. Cancel existing take-profit and place other take-profits if applicable
                    # 3. Update last_status
                    if not db_pos.position_id:
                        db_pos.position_id = server_pos['positionId']
                        db_pos.current_volume = Decimal(server_pos['availableAmt'])

                        if db_pos.primary_volume != db_pos.current_volume:
                            db_pos.last_status = "PARTIALLY_FILLED"
                        else:
                            db_pos.last_status = "FILLED"

                    else:
                        # Check if take-profit has vanished
                        pass
                    pos_vanished_from_server = False
                    break
            # Position vanished from server
            # 1. Get data from position history
            # 2. Set some values
            # 3. Close position - rework of function may be needed
            if pos_vanished_from_server:
                db_pos.close_position()

    def poll_accounts_for_order_statuses(self):
        accounts = Account.objects.all()

        self.logger.info('Starting polling accounts...')

        for account in accounts:
            self.check_position_statuses_for_account(account)

    ##### ORDER MANAGEMENT STUFF #####
    def place_takes(self, account: Account, tool: str, volume: Decimal):
        pass

    def cancel_takes_and_stop(self, account: Account, tool: str):
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
