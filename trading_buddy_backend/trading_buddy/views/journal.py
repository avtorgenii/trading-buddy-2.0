from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import api_view

from trading_buddy.models import Trade
from trading_buddy.serializers import ShowTradeSerializer, UpdateTradeSerializer


class TradesResultsSetPagination(PageNumberPagination):
    # page and page_size query params
    page_size = 20
    page_size_query_param = 'page_size'  # allow client to override page size
    max_page_size = 100


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