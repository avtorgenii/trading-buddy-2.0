# Default version unless TAG was specified when running make command
TAG ?= latest

.PHONY: prep-front prep-back prep-nginx prep-backup prep-all

# Dev commands
prep-front:
	docker build --build-arg VITE_API_BASE_URL="http://backend:8000/api/v1" --build-arg VITE_API_SUFFIX="/api/v1" --build-arg VITE_API_BE_BASE_URL="/api/v1" -t avtopetrovich/tb-frontend:$(TAG) ./trading_buddy_fe/
	docker push avtopetrovich/tb-frontend:$(TAG)

prep-back:
	docker build -t avtopetrovich/tb-backend:$(TAG) ./trading_buddy_backend/
	docker push avtopetrovich/tb-backend:$(TAG)

prep-nginx:
	docker build -t avtopetrovich/tb-nginx:$(TAG) -f nginx.Dockerfile .
	docker push avtopetrovich/tb-nginx:$(TAG)

prep-backup:
	docker build -t avtopetrovich/tb-backup:$(TAG) -f backup.Dockerfile .
	docker push avtopetrovich/tb-backup:$(TAG)

prep-all: prep-back prep-front prep-nginx prep-backup


compose-dev:
	TAG=$(TAG) docker compose -f docker-compose.dev.yml --env-file .env.prod up --build -d


# Prod commands
compose-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml pull
	TAG=$(TAG) docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

stop-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml --env-file .env.prod down

logs-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml logs -f