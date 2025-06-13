from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from rest_framework import serializers
from .models import Position, Account, Tool
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


class ToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tool
        fields = ('name',)

    def to_representation(self, instance):
        data = super().to_representation(instance)

        # Access the custom parameter from context
        preprocess_mode = self.context.get('preprocess_mode')

        if preprocess_mode == 'bybit':
            data['name'] = instance.to_bybit_trading_view_convention()
        elif preprocess_mode == 'binance':
            data['name'] = instance.to_binance_trading_view_convention()

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


##### TRADING #####
class PositionToOpenSerializer(serializers.Serializer):
    account_name = serializers.CharField()
    tool = serializers.CharField()
    trigger_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20, min_value=0)
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
    tool = serializers.CharField()
    trigger_price = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20, min_value=0)
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
        return data


class CurrentPositionSerializer(serializers.Serializer):
    tool = serializers.CharField()
    avg_open = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20, min_value=0)
    pos_side = serializers.CharField(max_length=5)
    pnl = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    margin = serializers.DecimalField(decimal_places=12, default=0.00, max_digits=20)
    leverage = serializers.IntegerField(min_value=1)
    volume = serializers.DecimalField(decimal_places=12, max_digits=20)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        for field in ['avg_open', 'pnl', 'margin', 'volume']:
            if field in data:
                data[field] = clean_decimal_str(Decimal(data[field]))
        return data

class CancelPendingPositionSerializer(serializers.Serializer):
    tool = serializers.CharField()
    account_name = serializers.CharField()

class CancelLevelsSerializer(serializers.Serializer):
    side = serializers.CharField(max_length=5)
    cancel_levels = serializers.ListField(
        child=serializers.DecimalField(decimal_places=12, max_digits=20, allow_null=True),
    )

    def validate_cancel_levels(self, value):
        if len(value) != 2:
            raise serializers.ValidationError("cancel_levels must contain exactly 2 items.")
        return value
