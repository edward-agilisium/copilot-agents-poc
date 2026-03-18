import asyncio
import httpx
from azure.identity.aio import ClientSecretCredential

TENANT_ID = "b8869792-ee44-4a05-a4fb-b6323a34ca35"
CLIENT_ID = "916271d2-fd1a-4d18-bae2-47e47c8bd374" 
CLIENT_SECRET = "a1f8Q~q0chgSmBgoquRnNwd6jTmyMtU5MWRqsdl2"

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