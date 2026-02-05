# Default version unless TAG was specified when running make command
TAG ?= latest

.PHONY: prep-front prep-front-k8s prep-back prep-backup prep-monitoring prep-all prep-all-k8s

# Dev commands
prep-front:
	docker build --build-arg VITE_API_BASE_URL="http://backend:8000/api/v1" --build-arg VITE_API_SUFFIX="/api/v1" --build-arg VITE_API_BE_BASE_URL="/api/v1" -t avtopetrovich/tb-frontend:$(TAG) ./trading_buddy_fe/
	docker push avtopetrovich/tb-frontend:$(TAG)
	docker push avtopetrovich/tb-frontend:latest

prep-front-k8s:
	docker build --build-arg VITE_API_BASE_URL="http://backend-svc:8000/api/v1" --build-arg VITE_API_SUFFIX="/api/v1" --build-arg VITE_API_BE_BASE_URL="/api/v1" -t avtopetrovich/tb-frontend:$(TAG) ./trading_buddy_fe/
	docker push avtopetrovich/tb-frontend:$(TAG)
	docker push avtopetrovich/tb-frontend:latest

prep-back:
	docker build -t avtopetrovich/tb-backend:$(TAG) ./trading_buddy_backend/
	docker push avtopetrovich/tb-backend:$(TAG)
	docker push avtopetrovich/tb-backend:latest

prep-backup:
	docker build -t avtopetrovich/tb-backup:$(TAG) ./infra/vps-docker/backup/
	docker push avtopetrovich/tb-backup:$(TAG)
	docker push avtopetrovich/tb-backup:latest

prep-monitoring:
	docker build -t avtopetrovich/tb-alloy:$(TAG) ./infra/vps-docker/monitoring/alloy/
	docker build -t avtopetrovich/tb-loki:$(TAG) ./infra/vps-docker/monitoring/loki/
	docker push avtopetrovich/tb-alloy:$(TAG)
	docker push avtopetrovich/tb-alloy:latest
	docker push avtopetrovich/tb-loki:$(TAG)
	docker push avtopetrovich/tb-loki:latest


prep-all: prep-back prep-front prep-backup prep-monitoring

# When launching this command TAG is k8sv1.0
prep-all-k8s: TAG = k8sv1.0
prep-all-k8s: prep-back prep-front-k8s


compose-dev:
	TAG=$(TAG) docker compose -f docker-compose.dev.yml --env-file .env.dev up --build -d


# Prod commands
compose-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml pull
	TAG=$(TAG) docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

stop-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml --env-file .env.prod down

logs-prod:
	TAG=$(TAG) docker compose -f docker-compose.prod.yml logs -f