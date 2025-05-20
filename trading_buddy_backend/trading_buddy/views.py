from rest_framework.response import Response
from rest_framework.decorators import api_view

from .models import Position
from .serializers import PositionSerializer


@api_view(['GET'])
def get_data(request):
    positions = Position.objects.all()
    serializer = PositionSerializer(positions, many=True)
    return Response(serializer.data)

@api_view(['POST'])
def add_item(request):
    serializer = PositionSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()

    return Response(serializer.data)