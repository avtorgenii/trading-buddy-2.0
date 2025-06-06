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
    # Auth and user
    path('auth/register/', views.register),  # POST
    path('auth/login/', views.login),  # POST
    path('auth/logout/', views.logout),  # POST

    path('deposit/', views.update_deposit),  # PUT

    # Account
    path('accounts/', views.create_account),  # POST
    path('accounts/<str:account_name>/', views.delete_account),  # DELETE
    path('accounts/<str:account_name>/details/', views.get_deposit_and_account_details),  # GET
    path('accounts/<str:account_name>/risk-percent/', views.update_risk_for_account),  # PUT

    # Tools under specific account
    path('accounts/<str:account_name>/tools/', views.add_tool),  # POST
    path('accounts/<str:account_name>/tools/<str:tool_name>/', views.remove_tool),  # DELETE

    # Trading
    path('trading/positions/process/', views.process_position_data),  # POST
    # path('trading/positions/open/', views.open_position),  # POST
    # path('positions/cancel/', views.cancel_position),  # POST
]
