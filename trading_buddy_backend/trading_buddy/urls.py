from django.urls import path


def initialize_exchanges():
    """
    Called once on startup of the backend
    """
    from .models import Account
    from .services.exchanges.exchanges import BingXExc

    map = {
        "BingX": BingXExc,
        # "ByBit": ByBitExc
    }

    accounts = Account.objects.all()
    for account in accounts:
        map[account.exchange](account)  # simply initialize class to restore all listeners


initialize_exchanges()

from . import views

urlpatterns = [
    # Auth
    path('auth/register/', views.register),
    path('auth/login/', views.login),
    # path('auth/logout/', views.logout, name='logout'),

    # Accounts
    path('accounts/', views.create_account),  # POST
    path('accounts/details/', views.get_deposit_and_account_details),  # GET

    # Trading
    # path('positions/open/', views.open_position),  # POST
    # path('positions/cancel/', views.cancel_position),  # POST
]
