.PHONY: build up down clean soft_clean cache_info


build:
	docker-compose build --parallel

up:
	docker-compose up -d

down:
	docker-compose down

clean:
	docker-compose down -v
	docker system prune -af
	rm -rf .docker-cache

soft-clean:
	docker-compose down
	docker image prune -f

cache-info:
	@echo "Cache Docker:"
	@docker system df
	@echo "Volumes:"
	@docker volume ls | grep cache
