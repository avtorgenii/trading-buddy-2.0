import time
from threading import Thread
from django.core.management.base import BaseCommand
from loguru import logger

from ...models import Position
from ...services.exchanges.exchanges import BingXExc, ByBitExc, BingXPriceListener


exc_map = {"BingX": BingXExc, "ByBit": ByBitExc}


class Command(BaseCommand):
    help = 'Manager of websocket listeners which track price changes'

    def handle(self, *args, **options):
        logger.info('Initializing SINGLE instance of price listeners manager...')
        active_listeners = {}

        while True:
            try:
                # 1. Ищем активные позиции, которым нужен мониторинг
                active_positions = Position.objects.filter(
                    last_status__in=['NEW', 'PARTIALLY_FILLED']
                )

                needed_tools = set(p.tool.name for p in active_positions)

                # 2. ЗАПУСК НОВЫХ
                for pos in active_positions:
                    tool = pos.tool.name
                    if tool not in active_listeners:
                        logger.info(f'Initializing price listener for {tool}')

                        # Воссоздаем объекты (так как это отдельный процесс)
                        account = pos.account
                        ExcClass = exc_map.get(account.exchange)
                        if not ExcClass: continue

                        exc = ExcClass(account)
                        listener = BingXPriceListener(tool, exc)

                        t = Thread(target=listener.listen_for_events, daemon=True)
                        t.start()

                        active_listeners[tool] = {"listener": listener, "thread": t}

                # 3. ОСТАНОВКА СТАРЫХ (если позиция закрылась)
                current_running_tools = list(active_listeners.keys())
                for tool in current_running_tools:
                    if tool not in needed_tools:
                        logger.info(f"Stopping listener for {tool}")
                        active_listeners[tool]["listener"].stop_listening()
                        del active_listeners[tool]

                time.sleep(3)  # Пауза между проверками базы

            except Exception as e:
                logger.exception(f"Error in price listeners manager {e}")
                time.sleep(5)