# Rules of usage
1. Currently restricted to open multiple trades on one tool within one trading account, on server side you will be unable to do that, 
   but if you open it on exchange side, handling orders and positions system will **FAIL**.
2. All decimals have maximum 20 digits, of which 12 are reserved for places after coma, which means that when BTC or any
   other trading tool will approach price of 100mln, code should be updated.
3. For now, manual cancellation of any order on the exchange side, breaks logic flow.
4. Exchange restricts placing Stop-loss order above current price, so unless your take-profits are meticulously near your entry price, or are take-losses actually, you should be fine,
   otherwise you may need to place stop-loss orders manually on exchange side 

# General info
1. Datetimes in db are being saved in UTC.

# Running
## Database

Before running db, make sure you have created ```.env``` file in root directory, it should look like below:

```
DB_USER=<>
DB_PASSWORD=<>
```

Postgres is used, to run it simply execute command below in root directory:

```
docker-compose up -d
```