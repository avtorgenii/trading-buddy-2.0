import json
import time

from django.utils import timezone
from schedule import Scheduler

from decimal import Decimal
from ...models import Account, Position
from loguru import logger

from threading import Thread

from .exchanges import BingXExc, ByBitExc, Exchange

exc_map = {
    "BingX": BingXExc,
    "ByBit": ByBitExc
}


def format_dict_for_log(dict_data: dict | list) -> str:
    return json.dumps(dict_data, indent=2).replace("{", '').replace("}", '')


class OrderPoller:
    def __init__(self, interval_seconds: int = 5):
        self.scheduler = Scheduler()
        self.scheduler.every(interval_seconds).seconds.do(self.poll_accounts_for_position_statuses)

        self.logger = logger.bind(class_name=self.__class__.__name__)

    def run(self):
        # Blocking call
        while True:
            try:
                self.scheduler.run_pending()
            except:
                self.logger.exception('Uncaught exception in order poller cycle')
            time.sleep(1)

    def check_position_statuses_for_account(self, account: Account):
        exc = exc_map[account.exchange](account)

        current_positions_server = exc.get_current_positions()
        current_positions_db = Position.objects.filter(account=account)

        for db_pos in current_positions_db:
            tool = db_pos.tool.name
            # If position doesn't yet have an id, then it could not vanish
            pos_vanished_from_server = db_pos.server_position_id is not None

            for server_pos in current_positions_server:
                # One position per tool as in rules of usage
                if tool == server_pos['symbol']:
                    pos_vanished_from_server = False
                    last_status = db_pos.last_status
                    # If the position is on the server and its status is not filled, check for fill event
                    if last_status in ['NEW', 'PARTIALLY_FILLED']:
                        self.check_for_fill_event(exc, tool, db_pos, server_pos, last_status)
                    # If the position is on the server and its status is filled or partially filled - check for partial take-profit event
                    # No need to check for partial take-profit if position has only one take-profit
                    elif last_status in ['FILLED', 'PARTIALLY_FILLED'] and len(db_pos.take_profit_prices) > 1:
                        self.check_for_partial_take_profit_event(exc, tool, db_pos, server_pos)
                        pass
                    break
            if pos_vanished_from_server:
                self.finish_trade(exc, tool, db_pos)

    def poll_accounts_for_position_statuses(self):
        accounts = Account.objects.all()

        self.logger.info('Starting polling accounts for position statuses...')

        for account in accounts:
            self.check_position_statuses_for_account(account)

    ##### ORDER MANAGEMENT STUFF #####
    def check_for_fill_event(self, exc: Exchange, tool: str, db_pos: Position, server_pos: dict, last_status: str):
        self.logger.debug(f'Checking {tool} for fill event')
        db_pos.max_held_volume = Decimal(server_pos['availableAmt'])

        # Not sure if this would actually work for partially filled positions
        if last_status == 'NEW':
            db_pos.start_time = timezone.now()
            db_pos.server_position_id = server_pos['positionId']

        new_status = 'PARTIALLY_FILLED' if db_pos.primary_volume != db_pos.max_held_volume else 'FILLED'
        db_pos.last_status = new_status
        db_pos.save()

        # TODO not the best solution because it will try to delete price listener every time position is partially filled
        # Delete price listener if position was already filled
        if new_status != 'NEW':
            exc.delete_price_listener(tool)

        # Replace take-profits only if positions status has been changed
        if db_pos.last_status != last_status:
            # No need to replace existing stop-loss in any case because after it was placed along with primary order, BingX manages its size by itself
            take_profits = db_pos.take_profit_prices
            # No need to replace the only one take profit for the same reason as above
            if len(take_profits) > 1:
                # Cancel initial take-profit
                exc.cancel_take_profits_for_tool(tool)
                # Place new take-profits
                exc.place_take_profit_orders(tool, take_profits, db_pos.max_held_volume, db_pos.side)

    def check_for_partial_take_profit_event(self, exc: Exchange, tool: str, db_pos: Position, server_pos: dict):
        """
        Handles partial take-profit
        """
        self.logger.debug(f'Checking {tool} for partial take-profit event')

        db_pos.current_volume = Decimal(server_pos['availableAmt'])
        stop_loss_order, take_profit_orders = exc.get_open_orders(db_pos.server_position_id)

        # self.logger.debug(format_dict_for_log(stop_loss_order))
        # self.logger.debug(format_dict_for_log(take_profit_orders))

        last_status = db_pos.last_status
        if last_status == 'PARTIALLY_FILLED':
            success, _ = exc.cancel_primary_order_for_tool(tool, only_cancel=True)
            if not success:
                self.logger.critical(
                    f"Failed to cancel primary order for partially filled position which reached take-profit!")

        if not db_pos.breakeven:
            num_current_fully_unfilled_tps = 0

            # Only count fully unfilled takes
            for tp_order in take_profit_orders:
                if tp_order['status'] == 'NEW':
                    num_current_fully_unfilled_tps += 1

            num_initial_tps = len(db_pos.take_profit_prices)

            # Checks if stop-loss is ready to be moved to entry level
            if db_pos.move_stop_after - (num_initial_tps - num_current_fully_unfilled_tps) <= 0:
                success, msg = exc.cancel_stop_loss_for_tool(tool)

                if not success:
                    self.logger.critical(f"Failed to cancel stop loss while moving it to breakeven")

                    success, msg = exc.place_stop_loss_order(tool, db_pos.entry_price, db_pos.current_volume,
                                                             db_pos.side)

                    if not success:
                        self.logger.critical("Failed to place stop loss while moving it to breakeven")
                    else:
                        db_pos.breakeven = True
                        db_pos.save()

    def finish_trade(self, exc: Exchange, tool: str, db_pos: Position):
        """
        Handles both manual, caused by stop-loss or take-profit
        """
        self.logger.debug(f'Finishing trade for {tool}')
        net_profit, commission = exc.get_position_result(db_pos)
        self.logger.info(f'Net profit: {net_profit}, commission: {commission}')

        # Do not close position until receive data about it
        if net_profit and commission:
            db_pos.pnl_usd = net_profit
            db_pos.commission_usd = commission
            db_pos.close_position()
            self.logger.debug(f'Finished trade for {tool}')
        else:
            self.logger.warning(f'No bound orders were found for {tool}, trade has not been finished')


def init_poller() -> OrderPoller:
    """
    Starts OrderPoller in separate thread
    """
    poller = OrderPoller()
    poller_thread = Thread(target=poller.run, daemon=True)
    poller_thread.start()
    return poller
