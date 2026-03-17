import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

# Load environment variables
load_dotenv()

VDB_URL = os.getenv("VDB_URL")
VDB_API = os.getenv("VDB_API")

client = QdrantClient(
    url=VDB_URL,
    api_key=VDB_API
)

collection_name = "CopilotAgentDocs"

# Create collection (safe check)
existing = [c.name for c in client.get_collections().collections]

if collection_name not in existing:
    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=1536,
            distance=Distance.COSINE
        )
    )
    print("✅ Collection created")
else:
    print("⚠️ Collection already exists")

# Step 2: Create payload indexes (IMPORTANT)

# doc_id → linking with DB
client.create_payload_index(
    collection_name=collection_name,
    field_name="doc_id",
    field_schema=PayloadSchemaType.KEYWORD
)

# version → for version control
client.create_payload_index(
    collection_name=collection_name,
    field_name="version",
    field_schema=PayloadSchemaType.INTEGER
)

# file_name → filtering/search
client.create_payload_index(
    collection_name=collection_name,
    field_name="file_name",
    field_schema=PayloadSchemaType.KEYWORD
)
print("✅ Payload indexes ensured")
