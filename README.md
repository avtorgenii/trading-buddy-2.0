# Running
## .env
Create all your ```.env``` files in the root of the project dir
### .env.dev
Below is how your ```.env.dev``` must look like:
```
##### Docker Compose for volumes prefix naming #####
COMPOSE_PROJECT_NAME=trading-buddy


##### Frontend #####
VITE_API_BASE_URL=http://tb-backend:8000/api/v1
VITE_API_SUFFIX=/api/v1
VITE_API_BE_BASE_URL=/api/v1


##### Backend #####
SECRET_KEY=<>
# True means launching backend from IDE, and database in docker, False - both backend and database in docker
DEBUG=True

ALLOWED_HOSTS=localhost,127.0.0.1,tb-backend,nginx-proxy,<your_domain_or_public_ip_address>
CORS_CSRF_ALLOWED_ORIGINS=http://localhost,http://localhost:80,http://localhost:5173,http://localhost:3000,http://tb-frontend:3000,<protocol:your_domain_or_public_ip_address>

SESSION_COOKIE_SECURE=False
CSRF_COOKIE_SECURE=False
CSRF_COOKIE_HTTPONLY=False
CSRF_USE_SESSIONS=False
CSRF_COOKIE_SAMESITE='Lax'
CORS_ALLOW_CREDENTIALS=True


##### Database #####
DB_NAME=postgres
# Name of db service in docker-compose.yml or name of the host (localhost when running on local machine and database has exposed port)
DB_HOST=localhost
DB_USER=<>
DB_PASSWORD=<>

##### SSO #####
GOOGLE_OAUTH_CLIENT_ID=<>
GOOGLE_OAUTH_SECRET=<>
LOGIN_REDIRECT_URL=/trading
```

SSO ones are optional - app will run fine without them as well

### .env.prod
Production version is the same as dev one except for values below:
```
DEBUG=False
DB_HOST=db
```

### backup.env
Below is how your ```backup.env``` for dropbox backups must look like:
```
DROPBOX_REMOTE_PATH=<>
DROPBOX_APP_KEY=<>
DROPBOX_APP_SECRET=<>
DROPBOX_REFRESH_TOKEN=<>
```
If you want to run app ASAP you can skip backups setup, app will work fine without them as well 

Here is the guide I used to obtain all above variable values and setup dropbox for backing up in total: [guide](https://www.youtube.com/watch?v=GhG2aDsx9sE)
## Locally
### Docker compose
If you just want to try out the project locally you can use ```docker-compose.prod.yml``` for this - it relies on publically available images
and only requires you to have configured ```.env.prod```.

After creating and setting up ```.env.prod``` simpy run command below to launch app via docker from the root dir of the repo:
```
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```

### IDE
For running from IDE you need to complete steps below:
1. Clone repo
```git clone https://github.com/avtorgenii/trading-buddy-2.0.git```
2. Initialize ```venv``` for the backend:
```
cd trading-buddy-2.0/trading_buddy_backend
uv sync
```
If you don't have ```uv``` yet here is the [installation guide](https://docs.astral.sh/uv/getting-started/installation/)
3. Setup ```.env.prod``` and ```.env.dev``` as shown in section above

```.env.prod``` is required whenever backend is launched via docker, because backend **cannot reach database**
on ```localhost``` from its container by ```localhost``` hostname so it uses database's service name ```db```

```.env.dev``` is required when you are launching backend from IDE and backend **can reach** database via ```localhost```
name because **database's port is exposed**


4. Initialize SvelteKit frontend as in ```README.md``` instruction in ```trading_buddy_fe``` dir:
```
cd trading-buddy-2.0/trading_buddy_fe
npm install
```
5. During development, I ran database only in docker container so just run command below from root of the project 
to create container for database:
```
docker compose -f docker-compose.dev.yml --env-file .env.dev up -d --build
```
Stop all others containers except for database, launch backend and frontend via CLI and app will be available at ```http://localhost:5173/```:
```
# In backend dir
python manage.py runserver

# In frontend dir
npm run dev
```

Every time you add changes to database scheme in ```models.py``` you have to run commands below for changes to be applied:
```
python manage.py makemigrations
python manage.py migrate
```
Dockerfile for backend applies migrations for you on the build stage

# Usage
For more usage details check out [article on my blog](https://avtorgenii.github.io/blog/blog/2025-11-07-trading-buddy-2.0/)
## Rules of usage
1. Currently restricted to open multiple trades on the same tool within one trading account, on app side you will be unable to do that, 
   but if you open it on exchange side, handling orders and positions system will **FAIL**.
2. All decimals have maximum 20 digits, of which 12 are reserved for places after coma, which means that when BTC or any
   other trading tool will approach price of 100mln, code should be updated.
3. For now, manual cancellation of any order on the exchange side, breaks logic flow.
4. Exchange restricts placing Stop-loss order above current price, so unless your take-profits are meticulously near your entry price, or are take-losses actually, you should be fine,
   otherwise you may need to place stop-loss orders manually on exchange side 
5. If you have opened position on exchange side, but it is not in database, it won't show up in your current and pending positions

## General info
1. All datetimes are in UTC without any timezone info
2. Default mode of all trades is **Cross Margin**
