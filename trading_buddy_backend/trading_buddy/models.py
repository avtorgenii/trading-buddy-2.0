from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ForeignKey


class User(AbstractUser):
    email = models.EmailField(unique=True)
    deposit = models.DecimalField(decimal_places=2, default=0.00, max_digits=20)
    risk_percent = models.DecimalField(decimal_places=5, default=0.00, max_digits=10)

# Exchange account
class Account(models.Model):
    name = models.CharField(max_length=120)
    api_key = models.TextField()
    secret_key = models.TextField()
    user = ForeignKey('User', related_name='accounts', on_delete=models.CASCADE)

    class Meta:
        # Enforce that the combination of 'name' and 'user' must be unique
        unique_together = (('name', 'user'),)

class Tool(models.Model):
    name = models.CharField(max_length=120)
    MARKET_CHOICES = [
        ('crypto', 'Crypto'),
        ('fund', 'Fund'),
        ('forex', 'Forex'),
    ]
    market = models.CharField(max_length=50, choices=MARKET_CHOICES)
    account = models.ForeignKey(Account, related_name='tools', on_delete=models.CASCADE)

    class Meta:
        # Enforce that the combination of 'name' and 'user' must be unique
        unique_together = (('name', 'account'),)

# Position is temporary, all needed data from it will be transferred to connected Trade and then Position record will be removed
class Position(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='positions')

    SIDE_CHOICES = [
        ('LONG', 'Long'), # actual value in DB and human-readable name
        ('SHORT', 'Short'),
    ]
    side = models.CharField(max_length=5, choices=SIDE_CHOICES)

    leverage = models.IntegerField()

    trigger_price = models.DecimalField(decimal_places=12 , default=0.00, max_digits=20)
    entry_price = models.DecimalField(decimal_places=12, max_digits=20)
    stop_price = models.DecimalField(decimal_places=12, max_digits=20)

    take_profit_prices = models.JSONField(default=list)
    cancel_levels = models.JSONField(default=list)

    start_time = models.DateTimeField(null=True)

    move_stop_after = models.IntegerField()

    primary_volume = models.DecimalField(decimal_places=12, max_digits=20)
    current_volume = models.DecimalField(decimal_places=12, max_digits=20)

    fill_history = models.JSONField(default=list, null=True)  # e.g., [{"price": 101.5, "volume": 0.5}, ...]

    last_status = models.CharField(max_length=50, null=True)
    breakeven = models.BooleanField(default=False)

    pnl_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0)
    commission_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0)

    account = models.ForeignKey('Account', related_name='positions', on_delete=models.CASCADE)
    trade = models.OneToOneField('Trade',related_name='position' , on_delete=models.CASCADE)


class Trade(models.Model):
    SIDE_CHOICES = [
        ('LONG', 'Long'), # actual value in DB and human-readable name
        ('SHORT', 'Short'),
    ]
    side = models.CharField(max_length=5, choices=SIDE_CHOICES)

    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='trades')

    start_time = models.DateTimeField(null=True)
    end_time = models.DateTimeField(null=True)

    risk_percent = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    risk_usd = models.DecimalField(decimal_places=2, max_digits=10, default=0)
    pnl_usd = models.DecimalField(decimal_places=2, max_digits=10, default=0, help_text="Net profit, after commissions")
    commission_usd = models.DecimalField(decimal_places=2, max_digits=10, default=0)

    description = models.TextField(null=True)
    result = models.TextField(null=True)
    screenshot = models.ImageField(upload_to='screenshots', null=True)

    account = models.ForeignKey('Account', related_name='trades', on_delete=models.CASCADE)