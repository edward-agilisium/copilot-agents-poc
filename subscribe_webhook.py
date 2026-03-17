import asyncio
import httpx
from datetime import datetime, timedelta, timezone
from azure.identity.aio import ClientSecretCredential

# --- YOUR CREDENTIALS ---
TENANT_ID = "b8869792-ee44-4a05-a4fb-b6323a34ca35"
CLIENT_ID = "916271d2-fd1a-4d18-bae2-47e47c8bd374" 
CLIENT_SECRET = "a1f8Q~q0chgSmBgoquRnNwd6jTmyMtU5MWRqsdl2"

# The Copilot-agent POC Drive ID we fetched earlier
DRIVE_ID = "b!xg9rVrDtB06drKus5q1B18WpraEho8ZMlOdmBY4JmJsEBxinGmiTT6-BBfcF8FDy"


NGROK_URL = "https://kelly-noncadenced-phylis.ngrok-free.dev/webhook"

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
        "notificationUrl": NGROK_URL, 
        "resource": f"/drives/{DRIVE_ID}/root",
        "expirationDateTime": expiration,
        "clientState": "CopilotAgentPOC-Active" 
    }

    print(f"Sending subscription request to MS Graph for {NGROK_URL}...")
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