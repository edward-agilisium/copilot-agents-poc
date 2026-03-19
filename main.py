import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db import create_tables

from routes.upload import router as upload_router
from routes.query import router as query_router
from routes.browse import router as browse_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB
create_tables()

# Include routes
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(browse_router)


@app.get("/")
def home():
    return {"message": "Copilot Agent Running"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.on_event("startup")
async def startup_webhook_renewal():
    """Auto-renew SharePoint webhook subscription on startup and every 20 hours."""
    webhook_url = os.environ.get("WEBHOOK_BASE_URL")
    if not webhook_url:
        return

    async def renewal_loop():
        while True:
            try:
                from subscribe_webhook import create_subscription
                await create_subscription()
                print("✅ Webhook subscription renewed successfully.")
            except Exception as e:
                print(f"⚠️ Webhook renewal failed: {e}")
            await asyncio.sleep(20 * 3600)

    asyncio.create_task(renewal_loop())
