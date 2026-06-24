delete-db:
	docker compose down -v

up:
	docker compose up -d

db-migrate:
	uv run alembic revision --autogenerate -m "$(MSG)"