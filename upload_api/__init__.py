import logging
import azure.functions as func
import json
import os
from azure.storage.blob import BlobServiceClient, ContentSettings

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Upload API triggered")

    from services.auth import validate_pin
    if auth_error := validate_pin(req):
        return auth_error

    try:
        # 1. Parse Multipart Data
        # 'category' comes from FormData (req.form), not params
        category = "uncategorized"
        try:
            if req.form and "category" in req.form:
                category = req.form["category"]
        except ValueError:
            pass # Request body might not be form data
            
        # Fallback to params if not in form
        if category == "uncategorized":
            category = req.params.get("category", "uncategorized")
            
        category = category.lower()

        # 2. Get Files from Multipart
        files = list(req.files.values())
        if not files:
            return func.HttpResponse(
                json.dumps({"error": "No files received"}),
                status_code=400,
                mimetype="application/json"
            )

        # 3. Connection
        connection_string = (
            os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            or os.getenv("AzureWebJobsStorage")
        )
        if not connection_string:
            raise ValueError("Storage connection string missing")

        blob_service = BlobServiceClient.from_connection_string(connection_string)
        container_client = blob_service.get_container_client("pdfs")
        
        if not container_client.exists():
            container_client.create_container()

        uploaded_paths = []

        # 4. Upload Each File
        for file_item in files:
            # Use ORIGINAL filename
            filename = file_item.filename
            if not filename:
                filename = "uploaded_file.pdf"
            
            # Clean filename just in case
            filename = os.path.basename(filename)

            # Construct path: category/filename
            blob_path = f"{category}/{filename}"
            
            blob_client = container_client.get_blob_client(blob_path)
            
            # Check if file already exists
            if blob_client.exists():
                return func.HttpResponse(
                    json.dumps({
                        "error": "A document with this name already exists. Please rename the file or remove the existing document before uploading again."
                    }),
                    status_code=409,
                    mimetype="application/json"
                )

            # Read file content
            file_content = file_item.read()
            
            blob_client.upload_blob(
                file_content,
                overwrite=False,
                content_settings=ContentSettings(content_type="application/pdf")
            )
            
            uploaded_paths.append(blob_path)
            logging.info(f"Uploaded: {blob_path}")

        return func.HttpResponse(
            json.dumps({
                "message": "Upload successful",
                "category": category,
                "files": uploaded_paths
            }),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Upload API failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
