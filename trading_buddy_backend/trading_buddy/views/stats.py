from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view

from trading_buddy.serializers import PnLCalendarSerializer, YearMonthQuerySerializer, ToolsWithWinratesSerializer, \
    PnLProgressionSerializer


@extend_schema(responses=PnLCalendarSerializer)
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


@extend_schema(
    responses={
        200: OpenApiTypes.FLOAT,
    })
@api_view(['GET'])
def total_pnl_all(request):
    total_pnl = request.user.get_total_pnl(all_accounts=True)
    return Response(total_pnl)


@extend_schema(
    parameters=[YearMonthQuerySerializer],
    responses={
        200: OpenApiTypes.FLOAT,
    }
)
@api_view(['GET'])
def get_winrate(request):
    year = request.query_params.get('year')
    month = request.query_params.get('month')

    if year:
        year = int(year)
    if month:
        month = int(month)

    user = request.user
    win_rate = user.get_winrate(year=year, month=month)
    return Response(win_rate)


@extend_schema(
    parameters=[YearMonthQuerySerializer],
    responses={
        200: OpenApiTypes.INT,
    }
)
@api_view(['GET'])
def get_num_trades(request):
    year = request.query_params.get('year')
    month = request.query_params.get('month')

    if year and month:
        year = int(year)
        month = int(month)

        user = request.user
        num_trades = user.get_num_trades(year=year, month=month)
        return Response(num_trades)
    else:
        return Response({"error": "Year/month value are invalid"}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(responses=ToolsWithWinratesSerializer(many=True))
@api_view(['GET'])
def get_tools_with_biggest_win_rates(request):
    user = request.user
    tools_data = user.get_tools_with_biggest_winrates()
    serializer = ToolsWithWinratesSerializer(tools_data, many=True)
    return Response(serializer.data)


@extend_schema(responses=PnLProgressionSerializer(many=True))
@api_view(['GET'])
def get_pnl_progression_over_days(request):  # Fixed function name
    user = request.user
    progression_data = user.get_pnl_progression_over_days()
    serializer = PnLProgressionSerializer(progression_data, many=True)
    return Response(serializer.data)