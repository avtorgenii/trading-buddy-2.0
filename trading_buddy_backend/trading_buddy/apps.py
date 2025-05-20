from django.apps import AppConfig


class TradingBuddyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'trading_buddy'

    def ready(self):
        """
        This method is called by Django once, when the app registry is fully loaded.
        """
        from .models import Account
        from .services.exchanges.exchanges import BingXExc

        map = {
            "BingX": BingXExc,
            # "ByBit": ByBitExc
        }

        accounts = Account.objects.all()
        for account in accounts:
            map[account.exchange]()  # simply initialize class to restore all listeners
