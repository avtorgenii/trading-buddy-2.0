from datetime import datetime
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from rest_framework import serializers
from .models import Account, Trade
from django.core.exceptions import ValidationError as DjangoValidationError

"""
By default, DRF’s save() calls create(validated_data) with just one argument.
"""

User = get_user_model()


def clean_decimal_str(d: Decimal) -> str:
    s = format(d.normalize(), 'f')  # Fixed-point format without scientific notation
    return s.rstrip('0').rstrip('.') if '.' in s else s


##### AUTH #####
# For registration
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    ##### Field-level validators, called automatically when .is_valid() is run on the serializer #####
    def validate_email(self, value):
        try:
            validate_email(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Enter a valid email address.")

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")

        return value

    def validate_password(self, value):
        if len(value) < 6:
            raise serializers.ValidationError("Password must be at least 6 characters long.")
        if value.lower() in ["password", "123456", "qwerty"]:
            raise serializers.ValidationError("This password is too common.")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],  # because Django uses username to authenticate users
            email=validated_data['email'],
            password=validated_data['password']  # This gets hashed automatically thanks to create_user
        )
        return user


# For login
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)  # never return password in response

    def authenticate(self):
        email = self.validated_data.get('email')
        password = self.validated_data.get('password')

        try:
            user = User.objects.get(email=email)
            if user.check_password(password) and user.is_active:
                return user
            else:
                raise serializers.ValidationError('Invalid credentials.')
        except User.DoesNotExist:
            raise serializers.ValidationError('Invalid credentials.')


##### USER #####
class DepositSerializer(serializers.Serializer):
    deposit = serializers.DecimalField(decimal_places=2, default=0.00, max_digits=20, min_value=0)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'deposit' in data:
            data['deposit'] = clean_decimal_str(Decimal(data['deposit']))
        return data


##### ACCOUNT #####
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ['user']

        # Remove API keys from response
        extra_kwargs = {
            'api_key': {'write_only': True},
            'secret_key': {'write_only': True}
        }

    def create(self, validated_data):
        user = self.context.get('user')
        if user is None:
            raise serializers.ValidationError("User must be provided in serializer context.")

        # Assign the user to the account instance
        validated_data['user'] = user

        # Create and return the account instance
        return super().create(validated_data)


class DepositAndAccountDataSerializer(serializers.Serializer):
    deposit = serializers.DecimalField(decimal_places=5, default=0.00, max_digits=20)
    risk_percent = serializers.DecimalField(decimal_places=5, default=3.00, max_digits=10)
    available_margin = serializers.DecimalField(decimal_places=5, default=0.00, max_digits=20)
    pnl_usd = serializers.DecimalField(decimal_places=5, default=0.00, max_digits=20)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['deposit', 'risk_percent', 'available_margin', 'pnl_usd']:
            if field in data:
                data[field] = clean_decimal_str(Decimal(data[field]))
        return data


def get_trading_view_convention(name: str, exchange_name: str) -> str:
    """
    Private helper method to convert a tool's exchange format name
    into the convention required by TradingView for perpetual contracts.

    Example:
        - ("WLD-USDT", "BYBIT") -> "BYBIT:WLDUSDT.P"
        - ("BTCUSDT", "BINANCE") -> "BINANCE:BTCUSDT.P"
    """
    base_name = name
    exchange_name = exchange_name.upper()

    # If there's a hyphen (e.g., WLD-USDT), split and use the base
    if '-' in name:
        base_name = name.split('-')[0]
    # Otherwise, if it's concatenated (e.g., BTCUSDT), strip common quote currencies
    else:
        for quote in ['USDT', 'USD']:
            if name.endswith(quote):
                base_name = name[:-len(quote)]
                break  # Exit loop once a match is found

    return f'{exchange_name}:{base_name}USDT.P'


def get_tool_label(name: str) -> str:
    """
    Private helper method to convert a tool's exchange format name
    into the convention required by TradingView for perpetual contracts.

    Example:
        - "WLD-USDT" -> "WLDUSDT"
        - "BTCUSDT" -> "BTCUSDT"
    """
    base_name = name

    # If there's a hyphen (e.g., WLD-USDT), split and use the base
    if '-' in name:
        base_name = name.split('-')[0]
    # Otherwise, if it's concatenated (e.g., BTCUSDT), strip common quote currencies
    else:
        for quote in ['USDT', 'USD']:
            if name.endswith(quote):
                base_name = name[:-len(quote)]
                break  # Exit loop once a match is found

    return f'{base_name}USDT'


class ToolSerializer(serializers.Serializer):
    """
    Serializes a Tool object, with the ability to dynamically format
    the trading_view_format based on the exchange specified in the context.
    """
    label = serializers.CharField(write_only=True)
    trading_view_format = serializers.CharField(write_only=True)
    exchange_format = serializers.CharField()

    def to_representation(self, instance):
        """
        Overrides the default representation to format the output based on context.
        """
        # Get the default serialized data for the instance
        data = {}

        # Access the 'preprocess_mode' from the serializer's context
        preprocess_mode = self.context.get('preprocess_mode')

        source_name = getattr(instance, 'name', '')

        if not source_name:
            return data  # Return default data if source name is not available

        data['exchange_format'] = source_name
        data['trading_view_format'] = get_trading_view_convention(source_name, preprocess_mode.upper())
        data['label'] = get_tool_label(source_name)

        return data


class RiskSerializer(serializers.Serializer):
    risk_percent = serializers.DecimalField(decimal_places=5, default=3.00, max_digits=10, min_value=0)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if 'risk_percent' in data:
            data['risk_percent'] = clean_decimal_str(Decimal(data['risk_percent']))
        return data


class PnLCalendarSerializer(serializers.Serializer):
    pnl_by_day = serializers.DictField(
        child=serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20),
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)

        cleaned_data = {
            day: clean_decimal_str(Decimal(amount))
            for day, amount in data['pnl_by_day'].items()
        }

        return {'pnl_by_day': cleaned_data}


##### JOURNAL #####
class ShowTradeSerializer(serializers.ModelSerializer):
    # DRF automatically calls get_screenshot_url before to_representation to set this param
    screenshot_url = serializers.SerializerMethodField()

    class Meta:
        model = Trade
        exclude = ['screenshot']

    def get_screenshot_url(self, obj):
        request = self.context.get('request')
        if obj.screenshot:
            # # build_absolute_uri converts the relative URL to a full URL including domain
            return request.build_absolute_uri(obj.screenshot.url)
        return None

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if instance.account:
            data['account_name'] = instance.account.name
        else:
            data['account_name'] = None

        if instance.tool:
            data['tool_name'] = get_tool_label(instance.tool.name)
        else:
            data['tool_name'] = None

        start_time = data['start_time']
        end_time = data['end_time']

        data['start_time'] = datetime.fromisoformat(start_time.replace("Z", "+00:00")).strftime(
            "%B %d, %Y %H:%M") if start_time else None
        data['end_time'] = datetime.fromisoformat(end_time.replace("Z", "+00:00")).strftime(
            "%B %d, %Y %H:%M") if end_time else None

        del data['tool']
        del data['account']

        data['pnl_risk_ratio'] = instance.pnl_usd / instance.risk_usd

        for field in ['risk_usd', 'risk_percent', 'commission_usd', 'pnl_usd', 'pnl_risk_ratio']:
            if field in data:
                data[field] = f"{Decimal(data[field]):.2f}"

        return data


# Will be used to send description and/or result and/or screenshot and/or timeframe for trade
class UpdateTradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = ('screenshot', 'description', 'result', 'timeframe')


##### TRADING #####
class PositionToOpenSerializer(serializers.Serializer):
    tool = serializers.CharField()
    trigger_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20, min_value=0, allow_null=True)
    entry_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    stop_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    take_profits = serializers.ListField(
        child=serializers.DecimalField(decimal_places=10, max_digits=20)
    )
    move_stop_after = serializers.IntegerField(min_value=0, default=0, required=False)
    leverage = serializers.IntegerField(min_value=1)
    volume = serializers.DecimalField(decimal_places=10, max_digits=20, required=False, allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['trigger_p', 'entry_p', 'stop_p', 'volume']:
            if field in data and data[field] is not None:
                data[field] = clean_decimal_str(Decimal(data[field]))
        # Also clean each take_profit decimal string
        if 'take_profits' in data and data['take_profits'] is not None:
            data['take_profits'] = [clean_decimal_str(Decimal(tp)) for tp in data['take_profits']]
        return data

    def validate(self, data):
        # Call parent validation first
        data = super().validate(data)

        take_profits = data.get('take_profits', [])
        entry_p = data.get('entry_p')
        stop_p = data.get('stop_p')
        trigger_p = data.get('trigger_p')

        # If frontend sends trigger_p as null, convert it to 0, which basically means that we are trying to open limit order
        if trigger_p is None:
            data['trigger_p'] = 0

        if take_profits:
            if entry_p > stop_p:
                if entry_p and any(tp <= entry_p for tp in take_profits):
                    raise serializers.ValidationError("Take profits must be above entry price for long position")
            elif entry_p < stop_p:
                if entry_p and any(tp >= entry_p for tp in take_profits):
                    raise serializers.ValidationError("Take profits must be below entry price for short position")

        return data


class ProcessedPositionToOpenSerializer(serializers.Serializer):
    volume = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    margin = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    potential_loss = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    potential_profit = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['volume', 'margin', 'potential_loss', 'potential_profit']:
            if field in data:
                data[field] = clean_decimal_str(Decimal(data[field]))
        return data


class PendingPositionSerializer(serializers.Serializer):
    trade_id = serializers.IntegerField()
    tool = serializers.CharField()
    trigger_price = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20, min_value=0,
                                             allow_null=True)
    pos_side = serializers.CharField(max_length=5)
    entry_price = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    margin = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    leverage = serializers.IntegerField(min_value=1)
    volume = serializers.DecimalField(decimal_places=12, max_digits=20)
    cancel_levels = serializers.ListField(
        child=serializers.DecimalField(decimal_places=12, max_digits=20, allow_null=True),
    )

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['entry_price', 'trigger_price', 'margin', 'volume']:
            if field in data:
                data[field] = clean_decimal_str(Decimal(data[field]))

        if data['trigger_price'] == 0:
            data['trigger_price'] = None

        if 'cancel_levels' in data and data['cancel_levels'] is not None:
            cleaned_levels = []
            for val in data['cancel_levels']:
                if val is None:
                    cleaned_levels.append(None)
                else:
                    cleaned_levels.append(clean_decimal_str(Decimal(val)))
            data['cancel_levels'] = cleaned_levels
        return data


class CurrentPositionSerializer(serializers.Serializer):
    trade_id = serializers.IntegerField()
    tool = serializers.CharField()
    trading_view_format = serializers.CharField(read_only=True)
    avg_open = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20, min_value=0)
    pos_side = serializers.CharField(max_length=5)
    realized_pnl = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    current_pnl = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    margin = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    leverage = serializers.IntegerField(min_value=1)
    volume = serializers.DecimalField(decimal_places=12, max_digits=20)
    open_date = serializers.DateTimeField()
    current_pnl_risk_reward_ratio = serializers.DecimalField(decimal_places=4, default=0.00, max_digits=10)
    description = serializers.CharField(allow_blank=True, allow_null=True)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['avg_open', 'realized_pnl', 'margin', 'volume', 'current_pnl_risk_reward_ratio', 'current_pnl']:
            if field in data:
                data[field] = clean_decimal_str(Decimal(data[field]))

        data['open_date'] = datetime.fromisoformat(data['open_date'].replace("Z", "+00:00")).strftime("%B %d, %Y %H:%M")
        data['trading_view_format'] = get_trading_view_convention(data['tool'], self.context.get('exchange'))

        return data


class ToolExchangeFormatSerializer(serializers.Serializer):
    tool = serializers.CharField()


class CancelLevelsSerializer(serializers.Serializer):
    cancel_levels = serializers.ListField(
        child=serializers.DecimalField(decimal_places=12, max_digits=20, allow_null=True),
    )

    def validate_cancel_levels(self, value):
        if len(value) != 2:
            raise serializers.ValidationError("cancel_levels must contain exactly 2 items.")
        return value


class MaxLeveragesSerializer(serializers.Serializer):
    max_long_leverage = serializers.IntegerField()
    max_short_leverage = serializers.IntegerField()
