# Rules of usage
1. Currently restricted to open multiple trades on one tool within one trading account

# Running
## Database
Before running db, make sure you have created ```.env``` file in ```trading_buddy_backend/trading_buddy_backend``` directory, it look like below:
```
DB_USER=<>
DB_PASSWORD=<>
```
Postgres is used, to run it simply execute command below in ```trading_buddy_backend``` directory:
```
docker-compose up -d
```