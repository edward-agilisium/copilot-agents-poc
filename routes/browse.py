import httpx
from fastapi import APIRouter, Query, HTTPException
from azure.identity.aio import ClientSecretCredential
from config import TENANT_ID, CLIENT_ID, CLIENT_SECRET, DRIVE_ID


router = APIRouter()

async def get_token():
    """Fetches the MS Graph token (Reuse this if it's already in your file)"""
    cred = ClientSecretCredential(TENANT_ID, CLIENT_ID, CLIENT_SECRET)
    token = await cred.get_token("https://graph.microsoft.com/.default")
    await cred.close()
    return token.token

@router.get("/list-folder")
async def list_sharepoint_folder(folder_id: str = Query("root", description="ID of the folder to browse, defaults to root")):
    """
    Returns the contents of a specific SharePoint folder. 
    Separates items into 'folders' and 'files' for easy UI rendering.
    """
    token = await get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    # Determine the correct MS Graph URL based on whether we are at the root or drilling down
    if folder_id == "root":
        graph_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/root/children"
    else:
        graph_url = f"https://graph.microsoft.com/v1.0/drives/{DRIVE_ID}/items/{folder_id}/children"

    # We use $select to only pull the exact data Streamlit needs, making the API lightning fast
    graph_url += "?$select=id,name,folder,file,webUrl,size,lastModifiedDateTime"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(graph_url, headers=headers)
            
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.json())
                
            data = response.json()
            
            folders = []
            files = []
            
            # Sort the response into files and folders so Streamlit can render folders at the top
            for item in data.get("value", []):
                formatted_item = {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "url": item.get("webUrl"),
                    "last_modified": item.get("lastModifiedDateTime"),
                    "size": item.get("size", 0)
                }
                
                if "folder" in item:
                    # It's a directory
                    formatted_item["child_count"] = item["folder"].get("childCount", 0)
                    folders.append(formatted_item)
                else:
                    # It's a file
                    formatted_item["extension"] = item["name"].split(".")[-1].lower() if "." in item["name"] else "unknown"
                    files.append(formatted_item)
                    
            return {
                "status": "success",
                "current_folder_id": folder_id,
                "folders": folders,
                "files": files
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))