.PHONY: test test-domain test-services lint format check dev frontend-dev auth-smoke

test:
	pytest tests/ -v

test-domain:
	pytest tests/domain/ -v

test-services:
	pytest tests/services/ -v

lint:
	ruff check .

format:
	ruff format .

check:
	ruff check . && ruff format --check .

dev:
	uvicorn api.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

# Smoke-test the auth flow against a running local server (port 8000).
# Requires: TEST_SETUP_KEY, TEST_EMAIL, TEST_PASSWORD env vars.
# Example:
#   TEST_SETUP_KEY=mykey TEST_EMAIL=test@example.com TEST_PASSWORD=testpassword123 make auth-smoke
auth-smoke:
	@echo "--- setup-status ---"
	@curl -sc /tmp/dmrb_cookies http://localhost:8000/api/auth/setup-status | python3 -m json.tool
	@echo "--- claim admin ---"
	@curl -sc /tmp/dmrb_cookies -X POST http://localhost:8000/api/auth/setup \
	  -H 'Content-Type: application/json' \
	  -d '{"setup_key":"$(TEST_SETUP_KEY)","email":"$(TEST_EMAIL)","password":"$(TEST_PASSWORD)","password_confirm":"$(TEST_PASSWORD)"}' \
	  | python3 -m json.tool
	@echo "--- me ---"
	@curl -sb /tmp/dmrb_cookies http://localhost:8000/api/auth/me | python3 -m json.tool
	@echo "--- logout ---"
	@curl -sb /tmp/dmrb_cookies -X POST http://localhost:8000/api/auth/logout | python3 -m json.tool
	@echo "--- me after logout (expect 401) ---"
	@curl -sb /tmp/dmrb_cookies http://localhost:8000/api/auth/me; echo
