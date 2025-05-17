from rest_framework.response import Response
from rest_framework.decorators import api_view

from trading_buddy_backend.trading_buddy.models import Position


@api_view(['GET'])
def get_data(request):
    person = {'name': 'Dennis', 'age': 18}
    return Response(person)