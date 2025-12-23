import logging
import azure.functions as func
import os
import mimetypes

def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        # Base directory of this function (frontend/)
        BASE_DIR = os.path.dirname(os.path.realpath(__file__))

        # Get requested file from route
        filename = req.route_params.get("file")

        # Default file
        if not filename or filename == "/":
            filename = "index.html"

        # Build full path
        file_path = os.path.abspath(os.path.join(BASE_DIR, filename))

        # Security: prevent path traversal
        if not file_path.startswith(BASE_DIR):
            logging.warning(f"Blocked path traversal attempt: {filename}")
            return func.HttpResponse("Forbidden", status_code=403)

        # File existence check
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            logging.warning(f"File not found: {file_path}")
            return func.HttpResponse("Not Found", status_code=404)

        # Detect MIME type
        mimetype, _ = mimetypes.guess_type(file_path)
        if not mimetype:
            if filename.endswith(".css"):
                mimetype = "text/css"
            elif filename.endswith(".js"):
                mimetype = "application/javascript"
            elif filename.endswith(".html"):
                mimetype = "text/html"
            else:
                mimetype = "application/octet-stream"

        # Serve file
        with open(file_path, "rb") as f:
            return func.HttpResponse(
                f.read(),
                mimetype=mimetype
            )

    except Exception as e:
        logging.error(f"Critical error serving UI file: {str(e)}")
        return func.HttpResponse(
            "Server Error",
            status_code=500
        )
