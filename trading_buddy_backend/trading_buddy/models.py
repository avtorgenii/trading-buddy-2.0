import os
import uuid
from calendar import monthrange

from datetime import datetime
from decimal import Decimal
from itertools import accumulate

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import ForeignKey, Sum, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.contrib.postgres.fields import ArrayField

from trading_buddy.filters import TradeFilters


class User(AbstractUser):
    email = models.EmailField(unique=True)
    deposit = models.DecimalField(decimal_places=2, default=0.00, max_digits=20)
    current_account = models.OneToOneField('Account', related_name='+', on_delete=models.SET_NULL, null=True,
                                           blank=True)

    def _get_accounts(self, investing=False):
        if investing:
            return self.accounts.filter(exchange=Account.Exchange.INVESTING)
        return self.accounts.exclude(exchange=Account.Exchange.INVESTING)

    # All accounts means all 'trading' accounts, if investing trades are required specify 'all_accounts=True' and 'investing=True'
    # `all_accounts=False` means that only trades from current selected account will be fetched
    def get_pnl_calendar_data(self, year, month, all_accounts=False, investing=False):
        try:
            year = int(year)
            month = int(month)
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        except ValueError:
            return None, "Invalid year/month format. Use YYYY/MM"

        trades = Trade.objects.filter(
            end_time__isnull=False,
            end_time__range=(start_date, end_date)
        )

        if all_accounts:
            user_accounts = self._get_accounts(investing)
            trades = trades.filter(account__in=user_accounts)
        else:
            if not self.current_account:
                return None, "No account is chosen as current"
            trades = trades.filter(account=self.current_account)

        aggregated = (
            trades.annotate(day=TruncDate('end_time'))
            .values('day')
            .annotate(pnl=Sum('pnl_usd'))
            .order_by('day')
        )

        pnl_by_day = {
            entry['day'].strftime('%Y-%m-%d'): entry['pnl'] or 0
            for entry in aggregated
        }

        return pnl_by_day, None

    def get_total_pnl(self, all_accounts=False, investing=False):
        if all_accounts:
            user_accounts = self._get_accounts(investing)
            trades = Trade.objects.filter(account__in=user_accounts)
        else:
            if not self.current_account:
                return None, "No account is chosen as current"
            trades = Trade.objects.filter(account=self.current_account)

        total_pnl = trades.aggregate(total_pnl=Sum('pnl_usd'))['total_pnl']
        return round(total_pnl, 2) if total_pnl is not None else 0

    def get_winrate(self, year: int = None, month: int = None, investing=False):
        """
        :return: Winrate - number from 0 to 1
        """
        user_accounts = self._get_accounts(investing)

        if year and month:
            try:
                year = int(year)
                month = int(month)
                start_date = datetime(year, month, 1)
                end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
            except ValueError as e:
                return None, f"Invalid year/month: {e}"

            trades = Trade.objects.filter(
                end_time__isnull=False,
                start_time__isnull=False,
                end_time__range=(start_date, end_date),
                account__in=user_accounts,
            )
        else:
            trades = Trade.objects.filter(account__in=user_accounts, start_time__isnull=False, end_time__isnull=False)

        if trades:
            win_trades_num = sum(1 for trade in trades if trade.pnl_usd > 0)
            return round(win_trades_num / len(trades), 4)
        else:
            return 0

    def get_num_trades(self, year: int, month: int, investing=False):
        user_accounts = self._get_accounts(investing)

        try:
            year = int(year)
            month = int(month)
            start_date = datetime(year, month, 1)
            end_date = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        except ValueError as e:
            return None, f"Invalid year/month: {e}"

        trades = Trade.objects.filter(
            end_time__isnull=False,
            start_time__isnull=False,
            end_time__range=(start_date, end_date),
            account__in=user_accounts,
        )

        return len(trades)

    def get_tools_with_biggest_winrates(self, investing=False):
        user_accounts = self._get_accounts(investing)
        trades = Trade.objects.filter(account__in=user_accounts, start_time__isnull=False, end_time__isnull=False)

        tool_stats = {}
        for trade in trades:
            tool_name = trade.tool.name
            if tool_name not in tool_stats:
                tool_stats[tool_name] = {'tool': tool_name, 'total_trades': 0, 'winning_trades': 0, 'winrate': 0}
            tool_stats[tool_name]['total_trades'] += 1
            if trade.pnl_usd > 0:
                tool_stats[tool_name]['winning_trades'] += 1

        for tool_name, stats in tool_stats.items():
            if stats['total_trades'] > 0:
                stats['winrate'] = round(stats['winning_trades'] / stats['total_trades'], 2)

        return sorted(tool_stats.values(), key=lambda x: x['winrate'], reverse=True)

    def get_pnl_progression_over_days(self, investing=False):
        user_accounts = self._get_accounts(investing)
        trades = Trade.objects.filter(account__in=user_accounts, start_time__isnull=False, end_time__isnull=False)

        daily_pnl = (
            trades
            .annotate(day=TruncDate('end_time'))
            .values('day')
            .annotate(pnl=Sum('pnl_usd'))
            .order_by('day')
        )

        days = [entry['day'] for entry in daily_pnl]
        pnl_values = [entry['pnl'] or 0 for entry in daily_pnl]
        cumulative_pnl = list(accumulate(pnl_values))

        return [
            {
                'day': day.strftime('%Y-%m-%d'),
                'daily_pnl': round(float(pnl), 2),
                'cumulative_pnl': round(float(cum_pnl), 2)
            }
            for day, pnl, cum_pnl in zip(days, pnl_values, cumulative_pnl)
        ]

    def get_filtered_trades(self, filters: TradeFilters = None, investing=False):
        accounts = self._get_accounts(investing)
        trades = Trade.objects.filter(account__in=accounts)

        if not filters:
            return trades.order_by('-pk')

        conditions = Q()

        if filters.date_from:
            conditions &= Q(end_time__gte=filters.date_from)
        if filters.date_to:
            conditions &= Q(end_time__lte=filters.date_to)
        if filters.trade_setup:
            conditions &= Q(trade_setup__in=filters.trade_setup)
        if filters.profitable is not None:
            conditions &= Q(pnl_usd__gt=0) if filters.profitable else Q(pnl_usd__lte=0)
        if filters.side:
            conditions &= Q(side=filters.side)
        if filters.tool_name:
            conditions &= Q(tool__name__in=filters.tool_name)
        if filters.timeframe:
            conditions &= Q(timeframe__in=filters.timeframe)

        return trades.filter(conditions).order_by('-pk')


# Exchange account
class Account(models.Model):
    class Exchange(models.TextChoices):
        BINGX = 'BingX', 'BingX'  # actual value in DB and human-readable name
        BYBIT = 'ByBit', 'ByBit'
        INVESTING = 'Investing', 'Investing'

    name = models.CharField(max_length=120)
    risk_percent = models.DecimalField(decimal_places=7, default=3.00, max_digits=10)
    exchange = models.CharField(max_length=120, choices=Exchange.choices)
    api_key = models.CharField()
    secret_key = models.CharField()
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
    server_position_id = models.CharField(null=True, blank=False)

    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='positions')

    class Side(models.TextChoices):
        LONG = 'LONG', 'Long'
        SHORT = 'SHORT', 'Short'

    side = models.CharField(max_length=5, choices=Side.choices, null=True)

    leverage = models.IntegerField()

    trigger_price = models.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    entry_price = models.DecimalField(decimal_places=12, max_digits=20)
    stop_price = models.DecimalField(decimal_places=12, max_digits=20)

    take_profit_prices = ArrayField(
        base_field=models.DecimalField(decimal_places=12, max_digits=20),
        default=list
    )
    # Overhigh/overlow and take-profit level - ORDER IS CRUCIAL FOR LISTENERS AND DB LOGIC
    cancel_levels = ArrayField(
        base_field=models.DecimalField(decimal_places=12, max_digits=20),
        default=list
    )

    start_time = models.DateTimeField(null=True, help_text='The moment primary order of position was placed')
    move_stop_after = models.IntegerField()
    move_stop_after_rr = models.DecimalField(null=True, decimal_places=12, max_digits=20,
                                             validators=[MinValueValidator(1.0)],
                                             help_text='After which risk reward level move stop-loss to entry level, this variable holds reward value from the ratio')

    primary_volume = models.DecimalField(decimal_places=12, max_digits=20)
    current_volume = models.DecimalField(decimal_places=12, max_digits=20, default=0.0)
    max_held_volume = models.DecimalField(decimal_places=12, max_digits=20)

    last_status = models.CharField(max_length=50, null=True, default="NEW")
    breakeven = models.BooleanField(default=False)  # True if stop-loss is moved nearby entry, False if not

    pnl_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0, help_text='Net profit, after commissions')
    commission_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0,
                                         help_text='Trading fees, are always negative')

    account = models.ForeignKey('Account', related_name='positions', on_delete=models.RESTRICT)
    trade = models.OneToOneField('Trade', related_name='position', on_delete=models.CASCADE)

    @property
    def start_time_unix_ms(self):
        """Return start_time as Unix milliseconds"""
        if self.start_time:
            return int(self.start_time.timestamp() * 1000)
        return None

    def close_position(self, reason: str = None):
        """
        Called to transfer data to Trade when position is closed
        :return:
        """
        self.trade.end_time = timezone.now()
        self.trade.volume = self.max_held_volume
        self.trade.pnl_usd = self.pnl_usd
        self.trade.commission_usd = self.commission_usd
        self.trade.result = reason
        self.trade.save()
        self.delete()

    def save(self, *args, **kwargs):
        # Sort them in order as they are being approached by price if in favor of position, reverse=False - ascending
        self.take_profit_prices = sorted(self.take_profit_prices, key=Decimal, reverse=self.side == 'SHORT')
        # Configure default cancel levels
        self.cancel_levels = [
            self.cancel_levels[0] if len(self.cancel_levels) > 0 else None,  # overbuy/overlow
            self.take_profit_prices[0] if len(self.take_profit_prices) > 0 else None  # take-profit
        ]
        # Then call the original save method
        super().save(*args, **kwargs)


class Trade(models.Model):
    class Side(models.TextChoices):
        LONG = 'LONG', 'Long'
        SHORT = 'SHORT', 'Short'

    class TradeSetup(models.TextChoices):
        # (Ре)накопление
        ACC_BORDER_BREAKTHROUGH = 'ACC_BORDER_BREAKTHROUGH', '(Ре)накопление - Пробой верхней границы'
        ACC_BORDER_RETEST = 'ACC_BORDER_RETEST', '(Ре)накопление - Ретест верхней границы'
        ACC_CREEK_BREAKTHROUGH = 'ACC_CREEK_BREAKTHROUGH', '(Ре)накопление - Пробой крика'
        ACC_CREEK_RETEST = 'ACC_CREEK_RETEST', '(Ре)накопление - Ретест крика'
        ACC_SPRING = 'ACC_SPRING', '(Ре)накопление - Спринг'

        # (Ре)дистрибьюция
        DISTR_BORDER_RETEST = 'DISTR_BORDER_RETEST', '(Ре)дистрибьюция - Ретест нижней границы'
        DISTR_ICE_RETEST = 'DISTR_ICE_RETEST', '(Ре)дистрибьюция - Ретест льда'
        DISTR_UPTHRUST = 'DISTR_UPTHRUST', '(Ре)дистрибьюция - Аптраст'

        # Вульф
        BEAR_WOLFE = 'BEAR_WOLFE', 'Медвежий Вульф'
        BULL_WOLFE = 'BULL_WOLFE', 'Бычий Вульф'

        # Клинья
        DOWN_WEDGE_BREAKTHROUGH = 'DOWN_WEDGE_BREAKTHROUGH', 'Нисходящий клин - пробой верхней границы'
        DOWN_WEDGE_RETEST = 'DOWN_WEDGE_RETEST', 'Нисходящий клин - ретест верхней границы'
        UP_WEDGE_BREAKTHROUGH = 'UP_WEDGE_BREAKTHROUGH', 'Восходящий клин - пробой нижней границы'
        UP_WEDGE_RETEST = 'UP_WEDGE_RETEST', 'Восходящий клин - ретест нижней границы'

        # Каналы
        DOWN_CHANNEL_REBOUND = 'DOWN_CHANNEL_REBOUND', 'Нисходящий канал - отбой вниз от верхней границы'
        DOWN_CHANNEL_BREAKTHROUGH = 'DOWN_CHANNEL_BREAKTHROUGH', 'Нисходящий канал - пробой верхней границы'
        DOWN_CHANNEL_RETEST = 'DOWN_CHANNEL_RETEST', 'Нисходящий канал - ретест верхней границы'
        UP_CHANNEL_REBOUND = 'UP_CHANNEL_REBOUND', 'Восходящий канал - пробой нижней границы'
        UP_CHANNEL_BREAKTHROUGH = 'UP_CHANNEL_BREAKTHROUGH', 'Восходящий канал - ретест нижней границы'
        UP_CHANNEL_RETEST = 'UP_CHANNEL_RETEST', 'Восходящий канал - отбой вверх от нижней границы'

        # Трендовые
        SECANT_RETEST = 'SECANT_RETEST', 'Ретест секущей в шорт'
        DOWN_TRENDLINE_REBOUND = 'DOWN_TRENDLINE_REBOUND', 'Отбой вниз от нисходящей трендовой'
        UP_TRENDLINE_REBOUND = 'UP_TRENDLINE_REBOUND', 'Отбой вверх от восходящей трендовой'

    side = models.CharField(max_length=5, choices=Side.choices)

    tool = models.ForeignKey(Tool, on_delete=models.RESTRICT, related_name='trades')

    # All datetimes are in utc
    start_time = models.DateTimeField(null=True, help_text='The moment primary order of position was placed')
    end_time = models.DateTimeField(null=True)

    risk_percent = models.DecimalField(decimal_places=7, max_digits=10, default=0)
    risk_usd = models.DecimalField(decimal_places=7, max_digits=20, default=0)
    pnl_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0, help_text="Net profit, after commissions")
    commission_usd = models.DecimalField(decimal_places=8, max_digits=20, default=0)

    timeframe = models.CharField(max_length=10, default='M15', null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    result = models.TextField(null=True, blank=True)

    trade_setup = models.CharField(null=True, blank=True, choices=TradeSetup.choices, max_length=100)
    tags = ArrayField(
        base_field=models.CharField(max_length=30),
        default=list,
        blank=True,
    )

    account = models.ForeignKey('Account', related_name='trades', null=True, on_delete=models.SET_NULL)

    def screenshot_upload_path(self, filename):
        account_id = self.account.id if self.account else 'unknown'
        user_id = "unknown"
        if account_id != 'unknown':
            user_id = self.account.user_id

        # Get file extension
        ext = os.path.splitext(filename)[1]
        new_filename = f"{self.pk or uuid.uuid4().hex}{ext}"

        return f'chart_screenshots/user_{user_id}/account_{account_id}/{new_filename}'

    # The actual image file URL relative to your media root is stored in screenshot.url
    # also has relative path: .name, absolute path, .path, actual file object: .file
    screenshot = models.ImageField(upload_to=screenshot_upload_path,
                                   null=True)  # screenshots folder inside MEDIA_ROOT, check settings.py

    @classmethod
    def create_trade(cls, side: str, account: Account, tool_name: str, risk_percent: Decimal, risk_usd: Decimal,
                     leverage: int, trigger_price: Decimal, entry_price: Decimal,
                     stop_price: Decimal, take_profits: list[Decimal], move_stop_after: int,
                     move_stop_after_rr: Decimal, primary_volume: Decimal,
                     start_time: datetime):
        """
        Creates trade and linked position.
        :return:
        """
        try:
            tool_obj = Tool.objects.get(account=account, name=tool_name)
        except Tool.DoesNotExist:
            tool_obj = Tool.objects.create(account=account, name=tool_name)

        trade = cls.objects.create(side=side, tool=tool_obj, risk_percent=risk_percent, risk_usd=risk_usd,
                                   account=account, start_time=start_time)

        Position.objects.create(tool=tool_obj, side=side, leverage=leverage, trigger_price=trigger_price,
                                entry_price=entry_price,
                                stop_price=stop_price, take_profit_prices=take_profits,
                                move_stop_after=move_stop_after, move_stop_after_rr=move_stop_after_rr,
                                primary_volume=primary_volume, max_held_volume=0,
                                account=account, trade=trade, start_time=start_time)

        return trade
