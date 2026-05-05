from django.db import models
from django.db.models import Window, OuterRef, Count, Subquery, Case, When, IntegerField
from django.db.models.functions import RowNumber
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from loguru import logger
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import api_view

from trading_buddy.filters import TradeFilters
from trading_buddy.models import Trade
from trading_buddy.serializers import ShowTradeSerializer, UpdateTradeSerializer, CreateInvestmentSerializer


class TradesResultsSetPagination(PageNumberPagination):
    # page and page_size query params
    page_size = 20
    page_size_query_param = 'page_size'  # allow client to override page size
    max_page_size = 100


def get_trade_number_subquery(user):
    """Returns a subquery that counts how many trades this user had before this trade (by pk)"""
    return (
        Trade.objects.filter(
            account__user=user,
            pk__lte=OuterRef('pk')
        )
        .order_by()
        .values('account__user')
        .annotate(cnt=Count('pk'))
        .values('cnt')
    )


def get_trade_stats(trades_qs):
    logger.debug(f"get_trade_stats query: {trades_qs.query}")
    stats = trades_qs.aggregate(
        total=Count('id'),
        profitable=Count(Case(When(pnl_usd__gt=0, then=1), output_field=IntegerField())),
        losing=Count(Case(When(pnl_usd__lt=0, then=1), output_field=IntegerField())),
        missed=Count(Case(When(pnl_usd=0, then=1), output_field=IntegerField())),
    )
    logger.debug(f"get_trade_stats result: {stats}")
    total = stats['total']
    stats['winrate'] = round(stats['profitable'] / (total - stats['missed']), 4) if total > 0 else 0
    return stats


@extend_schema(responses=ShowTradeSerializer(many=True))
@api_view(['GET'])
def get_all_trades(request):
    trades = (
        Trade.objects.filter(account__user=request.user).exclude(account__exchange='Investing')
        .annotate(trade_number=Subquery(get_trade_number_subquery(request.user)))
        .order_by('-pk')
    )
    paginator = TradesResultsSetPagination()
    result_page = paginator.paginate_queryset(trades, request)
    serializer = ShowTradeSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def get_filtered_trades(request):
    logger.debug(f"get_filtered_trades params: {request.query_params}")
    filters = TradeFilters.from_request(request)
    logger.debug(f"parsed filters: {filters}")
    try:
        trades = (
            request.user.get_filtered_trades(filters)
            .annotate(trade_number=Subquery(get_trade_number_subquery(request.user)))
        )
        logger.debug(f"trades count: {trades.count()}")
        stats = get_trade_stats(trades)
        logger.debug(f"stats: {stats}")
        serializer = ShowTradeSerializer(trades, many=True, context={'request': request})
        return Response({'trades': serializer.data, 'stats': stats})
    except Exception as e:
        logger.exception(f"get_filtered_trades failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



@extend_schema(responses=ShowTradeSerializer(many=True))
@api_view(['GET'])
def get_all_investments(request):
    trades = (
        Trade.objects.filter(account__user=request.user, account__exchange='Investing')
        .annotate(trade_number=Subquery(get_trade_number_subquery(request.user)))
        .order_by('-pk')
    )
    paginator = TradesResultsSetPagination()
    result_page = paginator.paginate_queryset(trades, request)
    serializer = ShowTradeSerializer(result_page, many=True, context={'request': request})
    return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def get_filtered_investments(request):
    logger.debug(f"get_filtered_investments params: {request.query_params}")
    filters = TradeFilters.from_request(request)
    logger.debug(f"parsed filters: {filters}")
    try:
        trades = (
            request.user.get_filtered_trades(filters, investing=True)
            .annotate(trade_number=Subquery(get_trade_number_subquery(request.user)))
        )
        logger.debug(f"trades count: {trades.count()}")
        stats = get_trade_stats(trades)
        logger.debug(f"stats: {stats}")
        serializer = ShowTradeSerializer(trades, many=True, context={'request': request})
        return Response({'trades': serializer.data, 'stats': stats})
    except Exception as e:
        logger.exception(f"get_filtered_investments failed: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@extend_schema(
    request=UpdateTradeSerializer
)
@api_view(['PUT', 'DELETE'])
def journal_trade(request, trade_id):
    trade = get_object_or_404(Trade, pk=trade_id)

    if request.method == 'PUT':
        # Passing Trade instance into serializer constructor means it will update existing record, instead of creating new one
        # Partial means that serializer won't require all fields to be present for validation
        serializer = UpdateTradeSerializer(trade, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()  # saves updated fields including the image
            return Response(status=status.HTTP_204_NO_CONTENT)
        else:
            return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        if hasattr(trade, 'position'):  # trade.position if there is no position will throw an exception
            return Response({
                "error": "Cannot remove trade with connected non-closed position.\nCancel order or close opened position in Positions first."},
                status=status.HTTP_400_BAD_REQUEST)
        else:
            trade.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    return Response({"error": "Method not allowed."}, status=status.HTTP_405_METHOD_NOT_ALLOWED)


@extend_schema(request=CreateInvestmentSerializer)
@api_view(['POST'])
def create_investment(request):
    serializer = CreateInvestmentSerializer(data=request.data)
    if serializer.is_valid():
        trade = serializer.save()
        return Response({'id': trade.id}, status=status.HTTP_201_CREATED)
    return Response({'error': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
