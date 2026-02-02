from django.core.management.base import BaseCommand
from loguru import logger

from ...services.exchanges.pollers import OrderPoller


class Command(BaseCommand):
    help = 'Launches SINGLE instance of OrderPoller'

    def handle(self, *args, **options):
        logger.info('Initializing order poller...')

        # Thread тут больше не нужен, так как этот скрипт будет главным процессом в контейнере.
        poller = OrderPoller()
        poller.run()

        logger.info('Initialized order poller')