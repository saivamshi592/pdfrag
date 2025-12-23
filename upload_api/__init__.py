import logging
import azure.functions as func
import json
import os
from azure.storage.blob import BlobServiceClient

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Upload API triggered")

    try:
        # 1. Read category
        category = req.params.get("category", "uncategorized").lower()

        # 2. Read raw body (Azure Functions way)
        body = req.get_body()
        if not body:
            return func.HttpResponse(
                json.dumps({"error": "Empty request body"}),
                status_code=400,
                mimetype="application/json"
            )

        # 3. Blob storage connection
        # Safe lazy access to env var
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
        if not connection_string:
            # If we can't connect to storage, we MUST return error for upload
            return func.HttpResponse(
                json.dumps({"error": "Storage configuration missing"}),
                status_code=500,
                mimetype="application/json"
            )

        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_name = "pdfs"

        container_client = blob_service.get_container_client(container_name)
        try:
            if not container_client.exists():
                container_client.create_container()
        except Exception as e:
            logging.warning(f"Container creation check failed (might already exist): {e}")

        # 4. TEMP filename (UI uploads single file)
        # In a real app, rely on Content-Disposition or generated UUID
        filename = "uploaded.pdf"
        blob_path = f"{category}/{filename}"

        blob_client = container_client.get_blob_client(blob_path)
        blob_client.upload_blob(body, overwrite=True)

        logging.info(f"Uploaded to {blob_path}")
        
        # Note: Embedding generation and Mongo insertion happen in the Blob Trigger.
        # If those fail, this API still returns success as the upload itself was successful.
        # This prevents the UI from showing an error when the background process is the issue.

        return func.HttpResponse(
            json.dumps({
                "message": "Upload successful",
                "path": blob_path
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Upload failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
