import os
from pathlib import Path
from datetime import datetime

# Azure Blob Storage SDK (azure-storage-blob) is required. Install with:
#   pip install azure-storage-blob

try:
    from azure.storage.blob import BlobServiceClient
except ImportError:
    raise RuntimeError("azure-storage-blob package not installed. Install it before running the backup script.")

# Expected environment variables
AZURE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER", "lucy-backups")

if not AZURE_CONNECTION_STRING:
    raise RuntimeError("AZURE_STORAGE_CONNECTION_STRING not set in environment")

# Folder we want to back up – the project data directory (SQLite DBs, logs, etc.)
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
EXPORTS_DIR = PROJECT_ROOT / "exports"

def _collect_paths():
    paths = []
    for base in [DATA_DIR, LOGS_DIR, EXPORTS_DIR]:
        if base.is_dir():
            for file_path in base.rglob("*.*"):
                if file_path.is_file():
                    paths.append(file_path)
    return paths

def upload_file(blob_service: BlobServiceClient, file_path: Path, blob_name: str):
    blob_client = blob_service.get_blob_client(container=AZURE_CONTAINER, blob=blob_name)
    with open(file_path, "rb") as data:
        blob_client.upload_blob(data, overwrite=True)
    print(f"Uploaded {file_path} -> {blob_name}")

def main():
    blob_service = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    # Ensure container exists
    try:
        blob_service.create_container(AZURE_CONTAINER)
        print(f"Created container '{AZURE_CONTAINER}'")
    except Exception:
        # Container likely already exists
        pass

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for file_path in _collect_paths():
        # Preserve relative path inside the container for easy restore
        relative = file_path.relative_to(PROJECT_ROOT)
        blob_name = f"backup_{timestamp}/{relative.as_posix()}"
        upload_file(blob_service, file_path, blob_name)
    print("Backup completed.")

if __name__ == "__main__":
    main()
