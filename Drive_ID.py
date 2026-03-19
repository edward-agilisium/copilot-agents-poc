import asyncio
import httpx
import json
from azure.identity.aio import ClientSecretCredential
from config import TENANT_ID, CLIENT_ID, CLIENT_SECRET

# Note: Using /drives (plural) to list all document libraries in the site
SITE_URL = "https://graph.microsoft.com/v1.0/sites/msvlforagileiss.sharepoint.com:/sites/copilot_agent:/drives"

async def get_drive_id():
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")

    headers = {
        "Authorization": f"Bearer {token.token}",
        "Accept": "application/json"
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SITE_URL, headers=headers)
        data = response.json()

        print("\n--- RAW JSON FROM MICROSOFT GRAPH ---")
        print(json.dumps(data, indent=2))
        print("-------------------------------------\n")

        if "value" in data and len(data["value"]) > 0:
            for drive in data["value"]:
                print(f"📁 Found Drive: {drive.get('name')}")
                print(f"🔑 COPY THIS ID: {drive.get('id')}\n")
        else:
            print("⚠️ The site was found, but no drives (Document Libraries) exist yet.")

if __name__ == "__main__":
    asyncio.run(get_drive_id())
