from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.status import HTTP_400_BAD_REQUEST

from trading_buddy.models import Account, Tool
from trading_buddy.serializers import AccountSerializer, DepositAndAccountDataSerializer, RiskSerializer, \
    DepositSerializer, ToolSerializer, AccountAPISerializer
from trading_buddy.services.exchanges.exchanges import BingXExc

# Exchanges map
exc_map = {
    "BingX": BingXExc,
    # "ByBit": ByBitExc
}


# Creating account and retrieving accounts
@extend_schema(
    methods=['GET'],
    responses=AccountSerializer(many=True),
)
@extend_schema(
    methods=['POST'],
    request=AccountSerializer,
)
@api_view(['GET', 'POST'])
def user_accounts(request):
    user = request.user

    if request.method == 'GET':
        accounts = user.accounts.all()
        serializer = AccountSerializer(accounts, many=True)
        return Response(serializer.data, status=200)

    elif request.method == 'POST':
        serializer = AccountSerializer(data=request.data, context={'user': user})
        if serializer.is_valid():
            new_account = serializer.save()

            is_valid = exc_map[new_account.exchange].check_account_validity(new_account.api_key, new_account.secret_key)

            if not is_valid:
                new_account.delete()
                return Response({"error": "Invalid API credentials"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Account created successfully"}, status=201)
        return Response({"errors": serializer.errors}, status=400)

    return Response({"error": "User doesn't exist"}, status=status.HTTP_400_BAD_REQUEST)


# Updating API keys of an account
@extend_schema(
    methods=['PUT'],
    request=AccountAPISerializer,
)
@api_view(['PUT'])
def update_account_api_keys(request):
    user = request.user

    serializer = AccountAPISerializer(data=request.data)
    if serializer.is_valid():
        account_id = serializer.validated_data['account_id']

        account = get_object_or_404(Account, pk=account_id)

        # For case when user tries to modify account which doesn't belong to him
        if account not in user.accounts.all():
            return Response({"error": "Bad boy :)"}, status=status.HTTP_400_BAD_REQUEST)

        api_key = serializer.validated_data['api_key']
        secret_key = serializer.validated_data['secret_key']

        is_valid = exc_map[account.exchange].check_account_validity(api_key, secret_key)

        if not is_valid:
            return Response({"error": "Invalid API credentials"}, status=status.HTTP_400_BAD_REQUEST)
        else:
            account.api_key = api_key
            account.secret_key = secret_key
            account.save()
            return Response({"message": "Account's API keys updated successfully"}, status=201)
    return Response({"errors": serializer.errors}, status=400)


# Delete account
@api_view(['DELETE'])
def delete_account(request, account_name):
    account = get_object_or_404(Account, name=account_name, user=request.user)
    account.delete()
    return Response({"message": "Account deleted successfully."}, status=200)


@api_view(['POST'])
def set_current_account(request, account_name):
    user = request.user
    account = get_object_or_404(Account, name=account_name, user=user)

    user.current_account = account
    user.save()
    return Response({"message": "Account set as current successfully."}, status=200)


# Get account details
@extend_schema(
    responses=DepositAndAccountDataSerializer
)
@api_view(['GET'])
def get_deposit_and_account_details(request):
    user = request.user
    account = user.current_account
    if not account:
        return Response({"error": "No account is chosen as current "}, status=400)

    exc = exc_map[account.exchange](account)

    success, msg, deposit, risk_percent, pnl, available_margin = exc.get_account_details()

    if success:
        serializer = DepositAndAccountDataSerializer(data={
            "deposit": deposit,
            "risk_percent": risk_percent,
            "available_margin": available_margin,
            "pnl_usd": pnl,
        })

        if serializer.is_valid():  # needed because constructing response from raw data, not models
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request=RiskSerializer,
)
@api_view(['PUT'])
def update_risk_for_account(request, account_name):
    serializer = RiskSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user
        account = Account.objects.filter(name=account_name, user=user).first()
        if not account:
            return Response({"error": "Account not found."}, status=400)

        account.risk_percent = serializer.validated_data['risk_percent']
        account.save()
        return Response({"message": "Risk updated successfully."}, status=status.HTTP_200_OK)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


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


##### TOOLS #####
# TODO IMPORTANT: ADD HINT FOR SUFFIX STYLE FOR ADD TOOL MODAL
@extend_schema(
    request=ToolSerializer,
    responses={
        200: ToolSerializer(many=True),
        201: {"description": "Tool added successfully"},
        400: {"description": "Bad request - account doesn't exist or tool already exists"}
    },
    methods=['GET', 'POST']
)
@api_view(['GET', 'POST'])
def manage_tools(request):
    user = request.user
    account = user.current_account

    if account is None:
        return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

    if request.method == 'GET':
        # Get all tools for the account
        tools = Tool.objects.filter(account=account)
        serializer = ToolSerializer(tools, many=True, context={'preprocess_mode': account.exchange.lower()})
        return Response(serializer.data, status=status.HTTP_200_OK)

    elif request.method == 'POST':
        # Add a new tool to the account
        serializer = ToolSerializer(data=request.data)
        if serializer.is_valid():
            try:
                Tool.objects.create(account=account, name=serializer.validated_data['name'])
                return Response({"message": "Tool added successfully"}, status=status.HTTP_201_CREATED)
            except IntegrityError:
                return Response({"error": "Tool already exists"}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# Remove tool
@api_view(['DELETE'])
def remove_tool(request, account_name, tool_name):
    user = request.user
    account = user.current_account

    if account is None:
        return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

    tool = Tool.objects.filter(account=account, name=tool_name).first()

    if tool is None:
        return Response({"error": "tool not found"}, status=404)

    tool.delete()
    return Response({"message": "Tool removed successfully"}, status=204)


@extend_schema(
    responses=ToolSerializer(many=True),
)
@api_view(['GET'])
def get_preset_tools(request):
    suffix = '-USDT'
    tool_names_bingx_format = ['BTC', 'XLM', 'GMT', 'ADA', 'TRU', 'LTC', 'POL', 'NEAR', 'TWT', 'FIL', 'LINK', 'APT',
                               'ATOM', 'UNI', 'TAO', 'ONDO', 'RENDER', 'DOGE', 'TIA', 'OP', 'DOT', 'BNB', 'DUCK', 'WLD',
                               'AVAX', 'VET', 'IOTA', 'KAS', 'ENA']

    tool_names_bingx_format = [tool + suffix for tool in tool_names_bingx_format]

    class DummyTool:
        def __init__(self, name):
            self.name = name

    dummy_tools_for_serialization = [DummyTool(name) for name in tool_names_bingx_format]

    preset_exchange_mode = 'bingx'  # bingx for exact price levels, analysis is made on binance

    serializer = ToolSerializer(
        dummy_tools_for_serialization,
        many=True,
        context={'preprocess_mode': preset_exchange_mode}
    )

    return Response(serializer.data, status=status.HTTP_200_OK)
