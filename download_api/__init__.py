import logging
import azure.functions as func
import os
from azure.storage.blob import BlobServiceClient
import urllib.parse

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Download API triggered")

    from services.auth import validate_pin
    if auth_error := validate_pin(req):
        return auth_error

    blob_path = req.params.get("blob")
    if not blob_path:
        return func.HttpResponse("Missing 'blob' parameter", status_code=400)

    # Security check: prevent directory traversal
    if ".." in blob_path or blob_path.startswith("/"):
        return func.HttpResponse("Invalid blob path", status_code=400)

    try:
        connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING") or os.getenv("AzureWebJobsStorage")
        if not connection_string:
            return func.HttpResponse("Storage connection missing", status_code=500)

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        # Using the same container 'pdfs' as defined in upload_api and blob_trigger
        container_client = blob_service_client.get_container_client("pdfs")
        blob_client = container_client.get_blob_client(blob_path)

        if not blob_client.exists():
            return func.HttpResponse(f"File not found: {blob_path}", status_code=404)

        # Download stream
        stream = blob_client.download_blob()
        file_bytes = stream.readall()

        # Content Disposition
        # filename is the last part of the path
        filename = blob_path.split("/")[-1]
        # Encode filename for header to handle spaces/special chars
        encoded_filename = urllib.parse.quote(filename)

        return func.HttpResponse(
            file_bytes,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f"attachment; filename={encoded_filename}; filename*=UTF-8''{encoded_filename}"
            },
            status_code=200
        )

    except Exception as e:
        logging.exception("Download failed")
        return func.HttpResponse(f"Server error: {str(e)}", status_code=500)
