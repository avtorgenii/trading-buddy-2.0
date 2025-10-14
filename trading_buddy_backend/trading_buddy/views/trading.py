from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST

from trading_buddy.serializers import MaxLeveragesSerializer, PositionToOpenSerializer, \
    ProcessedPositionToOpenSerializer, CancelLevelsSerializer, ToolExchangeFormatSerializer, PendingPositionSerializer, \
    CurrentPositionSerializer
from trading_buddy.services.exchanges.exchanges import BingXExc

# Exchanges map
exc_map = {
    "BingX": BingXExc,
    # "ByBit": ByBitExc
}

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

        if success:
            serializer = CurrentPositionSerializer(data=pending_data, many=True, context={'exchange': account.exchange})
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({"error": msg}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    return Response({"error": "No account is chosen as current."}, status=HTTP_400_BAD_REQUEST)
