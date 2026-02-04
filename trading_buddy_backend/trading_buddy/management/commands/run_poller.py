from django.core.management.base import BaseCommand
from loguru import logger

from ...services.exchanges.pollers import OrderPoller


class Command(BaseCommand):
    help = 'Launches SINGLE instance of OrderPoller'

    def handle(self, *args, **options):
        logger.info('Initializing order poller...')

        poller = OrderPoller()
        poller.run()

        logger.info('Initialized order poller')