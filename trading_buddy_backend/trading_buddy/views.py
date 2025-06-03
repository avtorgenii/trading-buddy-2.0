from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import login as django_login

from .models import Position
from .serializers import PositionSerializer, RegisterSerializer, LoginSerializer, DepositAndAccountDataSerializer, \
    AccountSerializer
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
"""


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
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Logging In
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
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


##### ACCOUNT #####
# Create an account
@api_view(['POST'])
def create_account(request):
    serializer = AccountSerializer(data=request.data, context={'user': request.user})
    if serializer.is_valid():
        account = serializer.save()  # will use create() with user set
        return Response(AccountSerializer(account).data, status=201)
    return Response(serializer.errors, status=400)


# Get account details
@api_view(['GET'])
def get_deposit_and_account_details(request):
    account_name = request.query_params.get('account_name')
    if not account_name:
        return Response({"error": "account_name is required"}, status=400)

    user = request.user
    account = user.accounts.filter(name=account_name).first()

    if account is None:
        return Response({"error": "account does not exist"}, status=400)

    map = {
        "BingX": BingXExc,
        # "ByBit": ByBitExc
    }

    exc = map[account.exchange](account)

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
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


##### TRADING #####
# Open position
# @api_view(['POST'])
# def open_position(request):
#     positions = Position.objects.all()
#     serializer = PositionSerializer(positions, many=True)
#     return Response(serializer.data)
#
#
# # Cancel position
# @api_view(['POST'])
# def cancel_position(request):
#     pass
