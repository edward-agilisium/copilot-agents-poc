import asyncio
import os
import sys
import httpx
from datetime import datetime, timedelta, timezone
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
DRIVE_ID = os.getenv("DRIVE_ID")

# Accept tunnel URL from: (1) CLI argument, (2) env var, (3) error
TUNNEL_URL = sys.argv[1] if len(sys.argv) > 1 else os.getenv("TUNNEL_URL")
if not TUNNEL_URL:
    print("❌ No tunnel URL provided. Pass as argument or set TUNNEL_URL env var.")
    sys.exit(1)

# Ensure URL ends with /webhook path
if not TUNNEL_URL.endswith("/webhook"):
    TUNNEL_URL = TUNNEL_URL.rstrip("/") + "/webhook"

async def create_subscription():
    print("Authenticating with Azure AD...")
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }

    # Webhook subscriptions expire. We set this one to live for 2 days.
    expiration = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    
    payload = {
        "changeType": "updated", # As we discovered, SharePoint Drives require 'updated'
        "notificationUrl": TUNNEL_URL, 
        "resource": f"/drives/{DRIVE_ID}/root",
        "expirationDateTime": expiration
    }

    print(f"Sending subscription request to MS Graph for {TUNNEL_URL}...")
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            "https://graph.microsoft.com/v1.0/subscriptions", 
            headers=headers, 
            json=payload
        )
        
        if response.status_code == 201:
            print("\n✅ SUCCESS! Subscription Created.")
            print(f"Subscription ID: {response.json().get('id')}")
            print("Your FastAPI server is now officially wired to SharePoint!")
        else:
            print(f"\n❌ API Error ({response.status_code}):\n{response.json()}")

    await cred.close()

if __name__ == "__main__":
    asyncio.run(create_subscription())