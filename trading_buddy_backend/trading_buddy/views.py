from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout

from .models import Position, Account, Tool
from .serializers import *
from .services.exchanges.exchanges import Exchange, BingXExc

"""
{
    "email": "test@gmail.com",
    "password": "123"
}

{
    "name": "BingX_Main",
    "exchange": "BingX",
    "api_key": "6NBKZNJeMfKCLviCZC4NhjKhnhhI60rnLqdPqurn49WITIYpFfHQE9GqgApK9OAZ1HDtz86GHDClGzuAplTEg",
    "secret_key": "IPwqlPr6kSo1Ik96mpCvCjD4eXaZS1z07Xm1WlcX3AwH8TxMeZT7PkwXiP2nVATwDLzuHndmeyblV5IaOxg"
}
{
    "name": "BTC"
}
{
    "deposit": 200.05
}
{
    "account_name": "BingX_Main",
    "tool": "WLD-USDT",
    "trigger_p": "1.0600",
    "entry_p": "1.0500",
    "stop_p": "1.0400",
    "take_profits": ["1.09", "1.1", "1.5"],
    "move_stop_after": "1",
    "leverage": "20"
}
{
    "account_name": "BingX_Main",
    "tool": "WLD-USDT",
    "trigger_p": "1.0600",
    "entry_p": "1.0500",
    "stop_p": "1.0400",
    "take_profits": ["1.09", "1.1", "1.5"],
    "move_stop_after": "1",
    "leverage": "20",
    "volume": "1.05"
}
"""

# Exchanges map
exc_map = {
    "BingX": BingXExc,
    # "ByBit": ByBitExc
}


##### AUTHORIZATION AND AUTHENTICATION #####
# Signing Up
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'User created successfully',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Logging In
@extend_schema(
    request=LoginSerializer,
)
@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.authenticate()

        # This is crucial — it creates the session cookie for the user
        django_login(request, user)

        return Response({
            'message': 'Logged in successfully',
            'user_id': user.id
        }, status=status.HTTP_200_OK)
    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Logging Out
@api_view(['POST'])
def logout(request):
    if request.user.is_authenticated:
        django_logout(request)
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)
    return Response({"error": "User is not authenticated."}, status=status.HTTP_400_BAD_REQUEST)


# Change deposit
@extend_schema(
    request=DepositSerializer,
)
@api_view(['PUT'])
def update_deposit(request):
    serializer = DepositSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user

        user.deposit = serializer.validated_data['deposit']
        user.save()

        return Response({"message": "Deposit updated successfully."}, status=status.HTTP_200_OK)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


##### ACCOUNT #####
# Create an account
##### AUTHORIZATION AND AUTHENTICATION #####
# Signing Up
@extend_schema(
    request=RegisterSerializer,
)
@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'User created successfully',
            'user_id': user.id
        }, status=status.HTTP_201_CREATED)
    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Creating account
@extend_schema(
    responses=AccountSerializer,
    request=AccountSerializer
)
@api_view(['POST'])
def create_account(request):
    serializer = AccountSerializer(data=request.data, context={'user': request.user})
    if serializer.is_valid():
        account = serializer.save()  # will use create() with user set
        return Response(AccountSerializer(account).data, status=201)
    return Response({"error": "".join(serializer.errors)}, status=400)


# Delete account
@api_view(['DELETE'])
def delete_account(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    account.delete()
    return Response({"message": "Account deleted successfully."}, status=204)


# Get account details
@extend_schema(
    responses=DepositAndAccountDataSerializer
)
@api_view(['GET'])
def get_deposit_and_account_details(request, account_name):
    if not account_name:
        return Response({"error": "account_name is required"}, status=400)

    user = request.user
    account = user.accounts.filter(name=account_name).first()

    if account is None:
        return Response({"error": "account does not exist"}, status=400)

    exc = exc_map[account.exchange](account)

    deposit, risk_percent, pnl, available_margin = exc.get_account_details()

    serializer = DepositAndAccountDataSerializer(data={
        "deposit": deposit,
        "risk_percent": risk_percent,
        "available_margin": available_margin,
        "pnl_usd": pnl,
    })

    if serializer.is_valid():
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=RiskSerializer,
)
@api_view(['PUT'])
def update_risk_for_account(request, account_name):
    serializer = RiskSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user

        user.accounts.filter(name=account_name).update(risk_percent=serializer.validated_data['risk_percent'])
        return Response({"message": "Risk updated successfully."}, status=status.HTTP_200_OK)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


##### TOOLS #####
# Add new tool
# TODO IMPORTANT: ADD HINT FOR SUFFIX STYLE FOR ADD TOOL MODAL
@extend_schema(
    request=ToolSerializer,
)
@api_view(['POST'])
def add_tool(request, account_name):
    serializer = ToolSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        account = user.accounts.filter(name=account_name).first()

        if account is None:
            return Response({"error": "account does not exist"}, status=400)

        try:
            Tool.objects.create(account=account, name=serializer.validated_data['name'])
            return Response({"message": "Tool added successfully"}, status=201)
        except IntegrityError:
            return Response({"error": "tool already exists"}, status=400)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Remove tool
@api_view(['DELETE'])
def remove_tool(request, account_name, tool_name):
    user = request.user
    account = user.accounts.filter(name=account_name).first()

    if account is None:
        return Response({"error": "account does not exist"}, status=400)

    tool = Tool.objects.filter(account=account, name=tool_name).first()

    if tool is None:
        return Response({"error": "tool not found"}, status=404)

    tool.delete()
    return Response({"message": "Tool removed successfully"}, status=204)


##### TRADING #####
# Get position data before opening
@extend_schema(
    request=PositionToOpenSerializer,
    responses=ProcessedPositionToOpenSerializer,
)
@api_view(['POST'])
def process_position_data(request):
    serializer = PositionToOpenSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    account = request.user.accounts.filter(name=data['account_name']).first()
    if not account:
        return Response({"error": "Account not found."}, status=status.HTTP_400_BAD_REQUEST)

    exc = exc_map[account.exchange](account)

    volume = data.get('volume')
    if volume is not None:
        margin = exc.calc_position_margin(data['entry_p'], volume, data['leverage'])
    else:
        volume, margin = exc.calc_position_volume_and_margin(
            data['tool'], data['entry_p'], data['stop_p'], data['leverage']
        )

    loss, profit = exc.calculate_position_potential_loss_and_profit(
        data['tool'], data['entry_p'], data['stop_p'], data['take_profits'], volume
    )

    result_data = {
        "volume": str(volume),
        "margin": str(margin),
        "potential_loss": str(loss),
        "potential_profit": str(profit),
    }

    result_serializer = ProcessedPositionToOpenSerializer(data=result_data)
    if result_serializer.is_valid():
        return Response(result_serializer.data, status=status.HTTP_200_OK)

    return Response({"error": "".join(result_serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

# Open position
# @api_view(['POST'])
# def place_position(request):
#     serializer = PositionToOpenSerializer(data=request.data)
#
#     if serializer.is_valid():
#         user = request.user
#         account = user.accounts.filter(name=account_name).first()
#
#         if account is None:
#             return Response({"error": "account does not exist"}, status=400)
#
#         exc = exc_map[account.exchange](account)
#
#     return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
#
#
# # Cancel position
# @api_view(['POST'])
# def cancel_position(request):
#     pass
