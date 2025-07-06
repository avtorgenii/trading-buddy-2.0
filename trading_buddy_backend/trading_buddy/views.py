from django.db import IntegrityError
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login as django_login
from django.contrib.auth import logout as django_logout
from rest_framework.status import HTTP_400_BAD_REQUEST

from .models import Tool
from .serializers import *
from .services.exchanges.exchanges import BingXExc

"""
{
    "email": "test@gmail.com",
    "password": "dizhihao!!!"
}

{
    "name": "BingX",
    "exchange": "BingX",
    "api_key": "6NBKZNJeMfKCLviCZC4NhjKhnhhI60rnLqdPqurn49WITIYpFfHQE9GqgApK9OAZ1HDtz86GHDClGzuAplTEg",
    "secret_key": "IPwqlPr6kSo1Ik96mpCvCjD4eXaZS1z07Xm1WlcX3AwH8TxMeZT7PkwXiP2nVATwDLzuHndmeyblV5IaOxg"
}
{
    "name": "WLD-USDT"
}
{
    "deposit": 200.05
}
{
    "tool": "WLD-USDT",
    "trigger_p": "1.0600",
    "entry_p": "1.0500",
    "stop_p": "1.0400",
    "take_profits": ["1.09", "1.1", "1.5"],
    "move_stop_after": "1",
    "leverage": "20"
}
{
    "tool": "WLD-USDT",
    "trigger_p": "0",
    "entry_p": "1.12",
    "stop_p": "1.06",
    "take_profits": ["1.14", "1.16"],
    "move_stop_after": "1",
    "leverage": "20",
    "volume": "3"
}
{
    "tool": "TRU-USDT",
    "trigger_p": null,
    "entry_p": "0.033",
    "stop_p": "0.035",
    "take_profits": ["0.03", "0.02"],
    "move_stop_after": "1",
    "leverage": "20",
    "volume": "100"
}
{
  "side": "LONG",
  "cancel_levels": [
    "1.1023", "1.4"
  ]
}
"""

# Exchanges map
exc_map = {
    "BingX": BingXExc,
    # "ByBit": ByBitExc
}


##### AUTHORIZATION AND AUTHENTICATION #####
# Sign status
@api_view(['GET'])
@permission_classes([AllowAny])
def auth_status(request):
    if request.user.is_authenticated:

        current_account_data = None

        if request.user.current_account:
            current_account_data = {
                'name': request.user.current_account.name,
                'exchange': request.user.current_account.exchange,
            }

        return Response({
            "logged_in": True,
            "email": request.user.email,
            "current_account": current_account_data
        }, status=status.HTTP_200_OK)
    else:
        return Response({"logged_in": False}, status=status.HTTP_401_UNAUTHORIZED)


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
        django_login(request, user)  # automatically log user in after registration
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
def update_risk_for_account(request):
    serializer = RiskSerializer(data=request.data)

    if serializer.is_valid():
        user = request.user
        account = user.current_account
        if not account:
            return Response({"error": "No account is chosen as current."}, status=400)

        account.update(risk_percent=serializer.validated_data['risk_percent'])
        return Response({"message": "Risk updated successfully."}, status=status.HTTP_200_OK)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


##### JOURNAL #####
class TradesResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'  # allow client to override page size
    max_page_size = 100


@extend_schema(
    responses=ShowTradeSerializer(many=True),  # not true, paginator makes response look different
)
@api_view(['GET'])
def get_trades(request):
    user = request.user
    account = user.current_account
    if not account:
        return Response({"error": "No account is chosen as current "}, status=400)

    trades = Trade.objects.filter(account=account).order_by('-pk')
    paginator = TradesResultsSetPagination()
    # Returns subset of trades for current page and page_size
    result_page = paginator.paginate_queryset(trades, request)
    serializer = ShowTradeSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    responses=ShowTradeSerializer(many=True),
)
@api_view(['GET'])
def get_all_trades(request):
    user = request.user

    trades = Trade.objects.filter(account__user=user).order_by('-pk')
    paginator = TradesResultsSetPagination()
    # Returns subset of trades for current page and page_size
    result_page = paginator.paginate_queryset(trades, request)
    serializer = ShowTradeSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@extend_schema(
    request=UpdateTradeSerializer
)
@api_view(['PUT'])
def update_trade(request, trade_id):
    trade = get_object_or_404(Trade, pk=trade_id)

    # Passing Trade instance into serializer constructor means it will update existing record, instead of creating new one
    # Partial means that serializer won't require all fields to be present for validation
    serializer = UpdateTradeSerializer(trade, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()  # saves updated fields including the image
        return Response(status=status.HTTP_204_NO_CONTENT)
    else:
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


##### STATS #####
@api_view(['GET'])
def pnl_calendar(request, year, month):
    pnl_by_day, error = request.user.get_pnl_calendar_data(year, month, all_accounts=False)
    if error:
        return Response({"error": error}, status=400)

    serializer = PnLCalendarSerializer({'pnl_by_day': pnl_by_day})
    return Response(serializer.data)


@extend_schema(responses=PnLCalendarSerializer)
@api_view(['GET'])
def pnl_calendar_all(request, year, month):
    pnl_by_day, error = request.user.get_pnl_calendar_data(year, month, all_accounts=True)

    if error:
        return Response({"error": error}, status=400)

    serializer = PnLCalendarSerializer({'pnl_by_day': pnl_by_day})
    return Response(serializer.data)


##### TOOLS #####
# Add new tool and get all tools under specific account
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


##### TRADING #####
@extend_schema(
    responses=MaxLeveragesSerializer
)
@api_view(['GET'])
def get_max_leverages(request, tool_name):
    """Tool name must be in appropriate exchange format"""
    user = request.user
    account = user.current_account
    if not account:
        return Response({"error": "No account is chosen as current "}, status=400)

    exc = exc_map[account.exchange](account)
    success, msg, max_long, max_short = exc.get_max_leverage(tool_name)

    if success:
        serializer = MaxLeveragesSerializer(data={'max_long_leverage': max_long, 'max_short_leverage': max_short})

        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Get position data before opening
@extend_schema(
    request=PositionToOpenSerializer,
    responses=ProcessedPositionToOpenSerializer,
)
@api_view(['POST'])
def process_position_data(request):
    serializer = PositionToOpenSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data
    account = request.user.current_account
    if account is None:
        return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

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


# Placing position
@extend_schema(
    request=PositionToOpenSerializer
)
@api_view(['POST'])
def place_position(request):
    serializer = PositionToOpenSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    data = serializer.validated_data

    user = request.user
    account = user.current_account
    tool_name = data['tool']

    if account:
        if account.positions.filter(tool__name=tool_name).exists():
            return Response({"error": "Cannot open multiple positions with the same tool within one account"},
                            status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

    if data.get('volume'):
        exc = exc_map[account.exchange](account)

        success, msg = exc.place_open_order(data['tool'], data['trigger_p'], data['entry_p'], data['stop_p'],
                                            data['take_profits'],
                                            data['move_stop_after'],
                                            data['leverage'], data['volume'])

        if success:
            return Response({"message": "Order placed successfully"}, status=status.HTTP_201_CREATED)
        else:
            return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    return Response({"error": "volume is required"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=CancelLevelsSerializer
)
@api_view(['PUT'])
def update_cancel_levels(request, tool_name):
    serializer = CancelLevelsSerializer(data=request.data)
    if serializer.is_valid():
        user = request.user
        account = user.current_account

        if account is None:
            return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

        account.positions.filter(tool__name=tool_name).update(cancel_levels=serializer.validated_data['cancel_levels'])
        return Response({"message": "Cancel levels updated successfully"}, status=status.HTTP_200_OK)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Cancel pending position
@extend_schema(
    request=ToolExchangeFormatSerializer
)
@api_view(['POST'])
def cancel_position(request):
    serializer = ToolExchangeFormatSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data

        user = request.user
        account = user.current_account
        tool_name = data['tool']

        pos = account.positions.filter(tool__name=tool_name).first()

        if account:
            if not pos:
                return Response({"error": "Position doesn't exist"},
                                status=status.HTTP_400_BAD_REQUEST)
            elif pos.last_status != "NEW":
                return Response({"error": "Position is already opened"}, status=status.HTTP_400_BAD_REQUEST)
            else:
                exc = exc_map[account.exchange](account)
                success, msg = exc.cancel_primary_order_for_tool(tool_name)
                if success:
                    return Response({"message": "Position cancelled successfully"}, status=status.HTTP_200_OK)
                else:
                    return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)

    return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=ToolExchangeFormatSerializer
)
@api_view(['POST'])
def close_position_by_market(request):
    serializer = ToolExchangeFormatSerializer(data=request.data)
    if serializer.is_valid():
        data = serializer.validated_data

        user = request.user
        account = user.current_account

        tool_name = data['tool']
        exc = exc_map[account.exchange](account)

        success, msg = exc.close_by_market(tool_name)

        if success:
            return Response({"message": msg}, status=status.HTTP_200_OK)
        else:
            return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    else:
        return Response({"error": "".join(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


# Get pending positions
@extend_schema(
    responses=PendingPositionSerializer(many=True)
)
@api_view(['GET'])
def get_pending_positions(request):
    user = request.user
    account = user.current_account

    if account:
        exc = exc_map[account.exchange](account)
        pending_data = exc.get_pending_positions_info()  # list of dicts

        serializer = PendingPositionSerializer(data=pending_data, many=True)
        if serializer.is_valid():
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)


# Get current positions
@extend_schema(
    responses=CurrentPositionSerializer(many=True)
)
@api_view(['GET'])
def get_current_positions(request):
    user = request.user
    account = user.current_account

    if account:
        exc = exc_map[account.exchange](account)
        success, msg, pending_data = exc.get_current_positions_info()  # list of dicts

        # print(pending_data)

        if success:
            serializer = CurrentPositionSerializer(data=pending_data, many=True, context={'exchange': account.exchange})
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)
