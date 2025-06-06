from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ForeignKey
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField


class User(AbstractUser):
    email = models.EmailField(unique=True)
    deposit = models.DecimalField(decimal_places=2, default=0.00, max_digits=20)


# Exchange account
class Account(models.Model):
    EXCHANGE_CHOICES = [
        ('BingX', 'BingX'),  # actual value in DB and human-readable name
        ('ByBit', 'ByBit'),
    ]
    name = models.CharField(max_length=120)
    risk_percent = models.DecimalField(decimal_places=5, default=3.00, max_digits=10)
    exchange = models.CharField(max_length=120, choices=EXCHANGE_CHOICES)
    api_key = models.TextField()
    secret_key = models.TextField()
    user = ForeignKey('User', related_name='accounts', on_delete=models.CASCADE)

    class Meta:
        unique_together = (('name', 'user'),)


class Tool(models.Model):
    name = models.CharField(max_length=120,
                            help_text="Tool name WITH exchange-appropriate suffix, e.g: BTC-USDT, not just BTC")
    account = models.ForeignKey(Account, related_name='tools',
                                on_delete=models.CASCADE)  # when account is deleted, all tools are deleted as well

    class Meta:
        # Enforce that the combination of 'name' and 'user' must be unique
        unique_together = (('name', 'account'),)


# Position is temporary, all needed data from it will be transferred to connected Trade and then Position record will be removed
class Position(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='positions')

    SIDE_CHOICES = [
        ('LONG', 'Long'),  # actual value in DB and human-readable name
        ('SHORT', 'Short'),
    ]
    side = models.CharField(max_length=5, choices=SIDE_CHOICES, null=True)

    leverage = models.IntegerField()

    trigger_price = models.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    entry_price = models.DecimalField(decimal_places=12, max_digits=20)
    stop_price = models.DecimalField(decimal_places=12, max_digits=20)

    take_profit_prices = ArrayField(
        base_field=models.DecimalField(decimal_places=12, max_digits=20),
        default=list
    )
    cancel_levels = ArrayField(
        base_field=models.DecimalField(decimal_places=12, max_digits=20),
        default=list
    )

    start_time = models.DateTimeField(null=True)

    move_stop_after = models.IntegerField()

    primary_volume = models.DecimalField(decimal_places=12, max_digits=20)
    current_volume = models.DecimalField(decimal_places=12, max_digits=20)

    fill_history = ArrayField(
        base_field=ArrayField(models.DecimalField(decimal_places=12, max_digits=20)),
        default=list,
        null=True
    )  # e.g., [[101.5, 0.5], []] price and volume tuples

    last_status = models.CharField(max_length=50, null=True, default="NEW")
    breakeven = models.BooleanField(default=False)  # True if stop-loss is moved nearby entry, False if not

    pnl_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0)
    commission_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0)

    account = models.ForeignKey('Account', related_name='positions', on_delete=models.RESTRICT)
    trade = models.OneToOneField('Trade', related_name='position', on_delete=models.CASCADE)

    def close_position(self):
        """
        Called to transfer data to Trade when position is closed
        :return:
        """
        self.trade.start_time = self.start_time
        self.trade.end_time = timezone.now()
        self.trade.volume = sum(item[1] for item in self.fill_history)
        self.trade.pnl_usd = self.pnl_usd
        self.trade.commission_usd = self.commission_usd
        self.delete()


class Trade(models.Model):
    SIDE_CHOICES = [
        ('LONG', 'Long'),  # actual value in DB and human-readable name
        ('SHORT', 'Short'),
    ]
    side = models.CharField(max_length=5, choices=SIDE_CHOICES)

    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='trades')

    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    risk_percent = models.DecimalField(decimal_places=5, max_digits=10, default=0)
    risk_usd = models.DecimalField(decimal_places=2, max_digits=20, default=0)
    pnl_usd = models.DecimalField(decimal_places=2, max_digits=20, default=0, help_text="Net profit, after commissions")
    commission_usd = models.DecimalField(decimal_places=2, max_digits=20, default=0)

    description = models.TextField(null=True)
    result = models.TextField(null=True)
    screenshot = models.ImageField(upload_to='screenshots', null=True)

    account = models.ForeignKey('Account', related_name='trades', null=True, on_delete=models.SET_NULL)

    @classmethod
    def create_trade(cls, side, account, tool_name, risk_percent, risk_usd, leverage, trigger_price, entry_price,
                     stop_price, take_profits, move_stop_after, primary_volume):
        """
        Creates trade and linked position.
        :return:
        """
        tool_obj = Tool.objects.get(account=account, name=tool_name)

        trade = cls.objects.create(side=side, tool=tool_obj, risk_percent=risk_percent, risk_usd=risk_usd)

        Position.objects.create(tool=tool_obj, side=side, leverage=leverage, trigger_price=trigger_price,
                                entry_price=entry_price,
                                stop_price=stop_price, take_profit_prices=take_profits, cancel_levels=[take_profits[0]],
                                move_stop_after=move_stop_after, primary_volume=primary_volume, current_volume=0,
                                account=account, trade=trade)
