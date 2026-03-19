import os
import json
import boto3
from dotenv import load_dotenv


def _load_secrets():
    """Fetch from AWS Secrets Manager if SECRETS_ARN is set, otherwise fall back to .env."""
    arn = os.environ.get("SECRETS_ARN")
    if arn:
        client = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-west-2"))
        raw = client.get_secret_value(SecretId=arn)["SecretString"]
        return json.loads(raw)
    load_dotenv()
    return {k: os.getenv(k) for k in [
        "TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "DRIVE_ID", "VDB_URL", "VDB_API"
    ]}


_secrets = _load_secrets()

TENANT_ID = _secrets["TENANT_ID"]
CLIENT_ID = _secrets["CLIENT_ID"]
CLIENT_SECRET = _secrets["CLIENT_SECRET"]
DRIVE_ID = _secrets["DRIVE_ID"]
VDB_URL = _secrets["VDB_URL"]
VDB_API = _secrets["VDB_API"]

DATA_DIR = os.environ.get("DATA_DIR", ".")
os.makedirs(os.path.join(DATA_DIR, "tmp"), exist_ok=True)

# Bedrock: IAM role on EC2 (no profile needed), local AWS profile for dev
_profile = os.environ.get("AWS_PROFILE") if not os.environ.get("SECRETS_ARN") else None
bedrock_session = boto3.Session(profile_name=_profile, region_name="us-west-2")
bedrock = bedrock_session.client("bedrock-runtime")
