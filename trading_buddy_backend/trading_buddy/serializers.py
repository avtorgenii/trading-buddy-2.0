from rest_framework import serializers
from .models import Position, User, Account, Tool

"""
By default, DRF’s save() calls create(validated_data) with just one argument.
"""


##### AUTH #####
# For registration
class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['email'],  # because Django uses username to authenticate users
            email=validated_data['email'],
            password=validated_data['password']  # This gets hashed automatically
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
        fields = ('name', )


##### TRADING #####
class PositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Position
        fields = '__all__'
