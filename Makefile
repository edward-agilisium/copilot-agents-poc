.PHONY: demo api tunnel webhook ui clean-webhooks

# Start everything with one command
demo:
	@bash start.sh

# Individual targets
api:
	uvicorn main:app --reload --port 8000

tunnel:
	cloudflared tunnel --url http://localhost:8000

webhook:
	python3.11 subscribe_webhook.py

ui:
	streamlit run app.py --server.port 8501

# Utility: remove all existing MS Graph subscriptions
clean-webhooks:
	python3.11 reset_webhooks.py
