import asyncio
import os
import httpx
from azure.identity.aio import ClientSecretCredential
from dotenv import load_dotenv

load_dotenv()

TENANT_ID = os.getenv("TENANT_ID")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

async def clean_slates():
    print("Authenticating with Azure AD...")
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")
    headers = {"Authorization": f"Bearer {token.token}"}

    async with httpx.AsyncClient() as client:
        print("🔍 Fetching all active subscriptions...")
        res = await client.get("https://graph.microsoft.com/v1.0/subscriptions", headers=headers)
        subs = res.json().get("value", [])

        if not subs:
            print("✅ No active subscriptions found.")
        else:
            for sub in subs:
                sub_id = sub['id']
                print(f"🗑️ Deleting subscription: {sub_id}...")
                await client.delete(f"https://graph.microsoft.com/v1.0/subscriptions/{sub_id}", headers=headers)
            print("🧹 Clean slate! All old webhooks deleted.")

    await cred.close()

if __name__ == "__main__":
    asyncio.run(clean_slates())