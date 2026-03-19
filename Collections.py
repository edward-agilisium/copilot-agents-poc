from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType
from config import VDB_URL, VDB_API

COLLECTION_NAME = "CopilotAgentDocs"
EMBEDDING_DIM = 1024  # ✅ Titan v2 dimension

# -----------------------------
# 2. INIT CLIENT
# -----------------------------
client = QdrantClient(
    url=VDB_URL,
    api_key=VDB_API
)

# -----------------------------
# 3. DROP EXISTING COLLECTION
# -----------------------------
existing_collections = [c.name for c in client.get_collections().collections]

if COLLECTION_NAME in existing_collections:
    print(f"⚠️ Collection '{COLLECTION_NAME}' exists. Deleting...")
    client.delete_collection(collection_name=COLLECTION_NAME)
    print("🗑️ Collection deleted")

# -----------------------------
# 4. CREATE NEW COLLECTION
# -----------------------------
print("🚀 Creating new collection with Titan v2 (1024 dim)...")

client.create_collection(
    collection_name=COLLECTION_NAME,
    vectors_config=VectorParams(
        size=EMBEDDING_DIM,
        distance=Distance.COSINE
    )
)

print("✅ Collection created successfully")

# -----------------------------
# 5. CREATE PAYLOAD INDEXES
# -----------------------------
print("📦 Creating payload indexes...")

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="doc_id",
    field_schema=PayloadSchemaType.KEYWORD
)

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="version",
    field_schema=PayloadSchemaType.INTEGER
)

client.create_payload_index(
    collection_name=COLLECTION_NAME,
    field_name="file_name",
    field_schema=PayloadSchemaType.KEYWORD
)

print("✅ Payload indexes created successfully")

# -----------------------------
# DONE
# -----------------------------
print("🎯 Qdrant is ready for Titan v2 embeddings!")