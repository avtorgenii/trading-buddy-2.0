from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import ForeignKey


class User(AbstractUser):
    email = models.EmailField(unique=True)
    deposit = models.DecimalField(decimal_places=2, default=0.00, max_digits=20)
    available_margin = models.DecimalField(decimal_places=2, default=0.00, max_digits=20)
    risk = models.DecimalField(decimal_places=5, default=0.00, max_digits=20)

class Account(models.Model):
    name = models.CharField(max_length=120)
    api_key = models.TextField()
    secret_key = models.TextField()
    user = ForeignKey('User', related_name='accounts', on_delete=models.CASCADE)

class Position(models.Model):
    tool = models.CharField(max_length=100)

    LONG = 'long'
    SHORT = 'short'
    SIDE_CHOICES = [
        (LONG, 'Long'),
        (SHORT, 'Short'),
    ]
    side = models.CharField(max_length=5, choices=SIDE_CHOICES)

    leverage = models.IntegerField()

    trigger_price = models.DecimalField(decimal_places=12 , default=0.00, max_digits=20)
    entry_price = models.DecimalField(decimal_places=12, max_digits=20)
    stop_price = models.DecimalField(decimal_places=12, max_digits=20)

    take_profit_prices = models.JSONField(default=list)
    cancel_levels = models.JSONField(default=list)

    move_stop_after = models.IntegerField()

    primary_volume = models.DecimalField(decimal_places=12, max_digits=20)
    current_volume = models.DecimalField(decimal_places=12, max_digits=20)

    fill_history = models.JSONField(default=list)  # e.g., [{"price": 101.5, "volume": 0.5}, ...]

    last_status = models.CharField(max_length=50)
    breakeven = models.BooleanField(default=False)

    pnl = models.DecimalField(decimal_places=8, max_digits=20)
    commission = models.DecimalField(decimal_places=8, max_digits=20)

    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    account = models.ForeignKey('Account', related_name='positions', on_delete=models.CASCADE)