# Rules of usage
1. Currently restricted to open multiple trades on one tool within one trading account, on server side you will be unable to do that, 
   but if you open it on exchange side, handling orders and positions system will **FAIL**.
2. All decimals have maximum 20 digits, of which 12 are reserved for places after coma, which means that when BTC or any
   other trading tool will approach price of 100mln, code should be updated.
3. For now, manual cancellation of any order on the exchange side, breaks logic flow.
4. Exchange restricts placing Stop-loss order above current price, so unless your take-profits are meticulously near your entry price, or are take-losses actually, you should be fine,
   otherwise you may need to place stop-loss orders manually on exchange side 
5. If you have opened position on exchange side, but it is not in database, it won't show up in your current positions

# General info
1. All datetimes are in UTC

# Running
## .env
Below is how your ```.env``` must look like:
```
# Backend
SECRET_KEY=<>
DEBUG=False
ALLOWED_HOSTS=localhost, 127.0.0.1
BACKEND_PORT=8000

# Frontend
FRONTEND_PORT=3000

# Database
DB_NAME=potgres
DB_HOST=db # name of db service in docker-compose.yml
DB_USER=<>
DB_PASSWORD=<>

# SSO
GOOGLE_OAUTH_CLIENT_ID=<>
GOOGLE_OAUTH_SECRET=<>
LOGIN_REDIRECT_URL=<>
```

## Database
Before running db, make sure you have created ```.env``` file in root directory and have migration files in ```trading_buddy_backend/trading_buddy/migrations```.

Postgres is used, to run it simply execute command below in root directory:

```
docker-compose up --build -d
```