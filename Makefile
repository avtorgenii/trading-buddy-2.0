# Dev commands
prep-front:
	docker build --build-arg VITE_API_BASE_URL="http://backend:8000/api/v1" --build-arg VITE_API_SUFFIX="/api/v1" --build-arg VITE_API_BE_BASE_URL="/api/v1" -t avtopetrovich/tb-frontend:1.0 ./trading_buddy_fe/
	docker push avtopetrovich/tb-frontend:1.0

prep-back:
	docker build -t avtopetrovich/tb-backend:1.0 ./trading_buddy_backend/
	docker push avtopetrovich/tb-backend:1.0

compose-dev:
	docker compose -f docker-compose.dev.yml --env-file .env.prod up --build -d


# Prod commands
compose-prod:
	docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

stop-prod:
	docker compose -f docker-compose.prod.yml --env-file .env.prod down

logs-prod:
	docker compose -f docker-compose.prod.yml logs -f