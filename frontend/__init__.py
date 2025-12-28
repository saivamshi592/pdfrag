import logging
import azure.functions as func
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Determine Base Directory safely
        try:
            BASE_DIR = os.path.dirname(os.path.realpath(__file__))
        except Exception:
            BASE_DIR = os.path.abspath(".")

        # Get the file path from route params safely
        filename = "index.html"
        if req.route_params and "file" in req.route_params:
            val = req.route_params.get("file")
            if val:
                filename = val

        # Handle root or empty
        if not filename or filename == "/":
            filename = "index.html"
        
        # Sanitize filename
        filename = filename.lstrip("/\\")

        # Resolve path
        file_path = os.path.abspath(os.path.join(BASE_DIR, filename))

        # Security check
        if not file_path.startswith(BASE_DIR):
            return func.HttpResponse("Forbidden", status_code=403)

        # Existence check
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logging.warning(f"File not found: {file_path}")
            return func.HttpResponse("Not Found", status_code=404)

        # Explicit MIME type handling
        mime_type = "application/octet-stream"
        lower_name = filename.lower()
        if lower_name.endswith(".html"):
            mime_type = "text/html; charset=utf-8"
        elif lower_name.endswith(".css"):
            mime_type = "text/css; charset=utf-8"
        elif lower_name.endswith(".js"):
            mime_type = "application/javascript; charset=utf-8"
        elif lower_name.endswith(".json"):
            mime_type = "application/json"
        elif lower_name.endswith(".png"):
            mime_type = "image/png"
        elif lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
            mime_type = "image/jpeg"
        elif lower_name.endswith(".ico"):
            mime_type = "image/x-icon"

        with open(file_path, "rb") as f:
            content = f.read()
            return func.HttpResponse(content, mimetype=mime_type)

    except Exception as e:
        logging.exception("Critical error serving UI file")
        # Return plain text error to avoid Azure Host error page if possible
        return func.HttpResponse(f"Server Error: {str(e)}", status_code=500)
