.PHONY: dev-client dev-server test-client test-server lint-client

dev-client:
	cd apps/client && pnpm dev

dev-server:
	cd apps/server && docker compose up --build

test-client:
	cd apps/client && pnpm test

test-server:
	cd apps/server && docker compose exec web python manage.py test

lint-client:
	cd apps/client && pnpm lint
