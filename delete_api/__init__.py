import logging
import azure.functions as func
import json
from services.mongo_store import mongo_store

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Delete Category API triggered.')

    from services.auth import validate_pin
    if auth_error := validate_pin(req):
        return auth_error

    try:
        category = req.params.get('category')
        if not category:
             # Try body
             try:
                 body = req.get_json()
                 category = body.get('category')
             except ValueError:
                 pass
        
        if not category:
            return func.HttpResponse(
                json.dumps({"error": "Missing category param"}),
                status_code=400,
                mimetype="application/json"
            )

        # Optional: delete specific PDF
        pdf_name = req.params.get('pdf_name')
        if not pdf_name:
            try:
                body = req.get_json()
                # body might have category and pdf_name
                # If category was found via params, body parsing might be skipped above, 
                # but let's re-parse body if we need pdf_name
                if body:
                    pdf_name = body.get('pdf_name')
            except ValueError:
                pass

        # Lazy import to avoid circular dependency or lighter init
        from azure.storage.blob import BlobServiceClient
        from config.settings import settings

        # Connect to Blob
        blob_service_client = None
        container_client = None
        if settings.AZURE_STORAGE_CONNECTION_STRING:
            try:
                blob_service_client = BlobServiceClient.from_connection_string(settings.AZURE_STORAGE_CONNECTION_STRING)
                container_client = blob_service_client.get_container_client("pdfs")
            except Exception as e:
                logging.error(f"Failed to connect to Blob Storage: {e}")

        if pdf_name:
            logging.info(f"Manual deletion requested for PDF: {category}/{pdf_name}")
            mongo_store.delete_pdf(category, pdf_name)
            
            # Delete Blob
            if container_client:
                blob_path = f"{category}/{pdf_name}"
                blob_client = container_client.get_blob_client(blob_path)
                if blob_client.exists():
                    blob_client.delete_blob()
                    logging.info(f"Deleted blob: {blob_path}")

            message = f"PDF '{pdf_name}' in category '{category}' deleted successfully."
        else:
            logging.info(f"Manual deletion requested for ENTIRE category: {category}")
            mongo_store.delete_category(category)
            
            # Delete Blobs in Category folder
            if container_client:
                prefix = f"{category}/"
                blobs = container_client.list_blobs(name_starts_with=prefix)
                for blob in blobs:
                    container_client.delete_blob(blob.name)
                logging.info(f"Deleted all blobs with prefix: {prefix}")

            message = f"Category '{category}' deleted successfully."
        
        return func.HttpResponse(
            json.dumps({"message": message}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("Delete failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
