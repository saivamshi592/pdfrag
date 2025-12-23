import logging
import azure.functions as func
import json
import os
from azure.storage.blob import BlobServiceClient
from config.settings import settings
from services.mongo_store import mongo_store

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Upload API triggered.')

    try:
        # 1. Parse Input
        # Note: In Azure V2 Python, req.files is the standard way.
        
        file_item = None
        category = "uncategorized"
        
        # PARAM priority
        category = req.params.get("category", req.form.get("category", "uncategorized"))

        if not req.files:
            return func.HttpResponse(
                json.dumps({"error": "No files found in request"}),
                status_code=400,
                mimetype="application/json"
            )

        # Task 2: Delete Category Logic (Safe Delete)
        # Execute ONCE before uploading any file in this batch
        if category and category.lower() != "uncategorized":
            logging.info(f"Wiping category '{category}' before upload (Replace Logic)")
            mongo_store.delete_category(category)

        uploaded_count = 0
        last_blob_path = ""
        
        # 2. Upload to Blob Storage
        connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        if not connection_string:
             raise ValueError("AzureWebJobsStorage not set")

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = "pdfs"
        
        try:
             blob_service_client.create_container(container_name)
        except Exception:
             pass

        container_client = blob_service_client.get_container_client(container_name)

        # Iterate all files
        for file_item in req.files.values():
            filename = file_item.filename
            content = file_item.stream.read()
            
            logging.info(f"Processing file: {filename}, Size: {len(content)}, Category: {category}")
            
            blob_path = f"{category}/{filename}"
            blob_client = container_client.get_blob_client(blob_path)
            blob_client.upload_blob(content, overwrite=True)
            
            logging.info(f"Uploaded to {container_name}/{blob_path}")
            uploaded_count += 1
            last_blob_path = blob_path

        return func.HttpResponse(
            json.dumps({
                "message": f"Successfully uploaded {uploaded_count} file(s).", 
                "path": last_blob_path,
                "count": uploaded_count
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
