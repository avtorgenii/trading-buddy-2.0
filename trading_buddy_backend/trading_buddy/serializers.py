from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from rest_framework import serializers
from .models import Position, Account, Tool
from django.core.exceptions import ValidationError as DjangoValidationError

"""
By default, DRF’s save() calls create(validated_data) with just one argument.
"""

User = get_user_model()


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
    deposit = serializers.DecimalField(decimal_places=2, default=0.00, max_digits=20)


##### ACCOUNT #####
class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ['user']

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


class ToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tool
        fields = ('name',)


class RiskSerializer(serializers.Serializer):
    risk_percent = serializers.DecimalField(decimal_places=5, default=3.00, max_digits=10)


##### TRADING #####
class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'


class PositionToOpenSerializer(serializers.Serializer):
    """
    Tool name should include exchange-appropriate suffix, which should be dealt on tool adding stadia
    """
    account_name = serializers.CharField()
    tool = serializers.CharField()
    trigger_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    entry_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    stop_p = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    take_profits = serializers.ListField(
        child=serializers.DecimalField(decimal_places=10, max_digits=20)
    )
    move_stop_after = serializers.IntegerField()
    leverage = serializers.IntegerField()
    volume = serializers.DecimalField(decimal_places=10, max_digits=20, required=False, allow_null=True)


class ProcessedPositionToOpenSerializer(serializers.Serializer):
    volume = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    margin = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    potential_loss = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
    potential_profit = serializers.DecimalField(decimal_places=10, default=0.00, max_digits=20)
