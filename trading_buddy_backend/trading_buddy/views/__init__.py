import sys
from .auth import *
from .account import *
from .journal import *
from .stats import *
from .trading import *
from ..services.exchanges.pollers import init_poller
from loguru import logger

# Initializing poller
_poller_initialized = False


def ensure_poller_initialized():
    global _poller_initialized
    if not _poller_initialized:
        poller = init_poller()
        logger.info('Initialized order poller')
        _poller_initialized = True


# Check if we're running a Django management command
def is_running_management_command():
    return len(sys.argv) >= 2 and sys.argv[1] in ['shell', 'shell_plus', 'makemigrations', 'migrate', 'test']


# # Only run if not in management command
# if not is_running_management_command():
#     ensure_poller_initialized()

# Sample data for API testing
"""
{
    "email": "test@gmail.com",
    "password": "dizhihao!!!"
}

{
    "name": "BingX",
    "exchange": "BingX",
    "api_key": "6NBKZNJeMfKCLviCZC4NhjKhnhhI60rnLqdPqurn49WITIYpFfHQE9GqgApK9OAZ1HDtz86GHDClGzuAplTEg",
    "secret_key": "IPwqlPr6kSo1Ik96mpCvCjD4eXaZS1z07Xm1WlcX3AwH8TxMeZT7PkwXiP2nVATwDLzuHndmeyblV5IaOxg"
}
{
    "name": "WLD-USDT"
}
{
    "deposit": 200.05
}
{
    "tool": "WLD-USDT",
    "trigger_p": "1.0600",
    "entry_p": "1.0500",
    "stop_p": "1.0400",
    "take_profits": ["1.09", "1.1", "1.5"],
    "move_stop_after": "1",
    "leverage": "20"
}
{
    "tool": "WLD-USDT",
    "trigger_p": "0",
    "entry_p": "1.12",
    "stop_p": "1.06",
    "take_profits": ["1.14", "1.16"],
    "move_stop_after": "1",
    "leverage": "20",
    "volume": "3"
}
{
    "tool": "TRU-USDT",
    "trigger_p": null,
    "entry_p": "0.033",
    "stop_p": "0.035",
    "take_profits": ["0.03", "0.02"],
    "move_stop_after": "1",
    "leverage": "20",
    "volume": "100"
}
{
  "side": "LONG",
  "cancel_levels": [
    "1.1023", "1.4"
  ]
}
"""
