.PHONY: up down logs restart status clean

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f postiz

restart: down up

status:
	docker compose ps

clean:
	@echo "WARNING: This removes all volumes (database data, uploads, etc.)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ] && docker compose down -v || echo "Aborted."
