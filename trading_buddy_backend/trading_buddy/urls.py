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
        if account.exchange == "BingX":
            map[account.exchange](account)  # simply initialize class to restore all listeners

    print("INITIALIZED EXCHANGES")


# Comment out while doing migrations
initialize_exchanges()

from . import views
from dj_rest_auth.registration.views import SocialLoginView
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter


urlpatterns = [
    ##### AUTH AND USER #####
    path('auth/register/', views.register),  # POST
    path('auth/login/', views.login),  # POST
    path('auth/logout/', views.logout),  # POST
    path('auth/status/', views.auth_status),  # GET

    path('deposit/', views.update_deposit),  # PUT

    ##### ACCOUNT(S) #####
    path('accounts/<str:account_name>/', views.set_current_account),  # POST
    path('accounts/', views.user_accounts),  # GET, POST
    path('account/details/', views.get_deposit_and_account_details),  # GET
    path('accounts/delete/<str:account_name>/', views.delete_account),  # DELETE
    path('account/risk-percent/', views.update_risk_for_account),  # PUT

    ##### STATS #####
    # All accounts
    path('stats/pnl-calendar/all/<int:year>/<int:month>/', views.pnl_calendar_all),  # GET

    # Specific account
    path('stats/pnl-calendar/<int:year>/<int:month>/', views.pnl_calendar),  # GET

    ##### JOURNAL #####
    # api/v1/stats/trades/all/?page=2&page_size=5
    path('journal/trades/all/', views.get_all_trades),  # GET, under all accounts, pagination query params are used, check views.py
    path('journal/trades/', views.get_trades),  # GET, under current selected account, pagination query params are used, check views.py

    path('journal/trades/<int:trade_id>', views.update_trade), # PUT

    # Preset list of tools
    path('trading/tools/', views.get_preset_tools),  # GET

    # Tools under specific account
    path('account/tools/', views.manage_tools),  # GET, POST
    path('account/tools/<str:tool_name>/', views.remove_tool),  # DELETE

    # Trading under specific account
    path('trading/tools/<str:tool_name>/leverages', views.get_max_leverages),  # GET
    path('trading/positions/process/', views.process_position_data),  # POST
    path('trading/positions/place/', views.place_position),  # POST
    path('trading/positions/cancel/', views.cancel_position),  # POST
    path('trading/positions/close-by-market/', views.close_position_by_market),  # POST
    path('trading/positions/pending/cancel-levels/<str:tool_name>/', views.update_cancel_levels), # PUT
    path('trading/positions/pending/', views.get_pending_positions),  # GET
    path('trading/positions/current/', views.get_current_positions),  # GET
]
