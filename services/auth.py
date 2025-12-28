import os
import logging
import json
import azure.functions as func

def validate_pin(req: func.HttpRequest) -> func.HttpResponse:
    """
    Validates the 'x-access-pin' header against the environment variable 'ACCESS_PIN'.
    Returns None if valid, or a 401/500 func.HttpResponse if invalid/error.
    """
    env_pin = os.environ.get("ACCESS_PIN")
    
    if not env_pin:
        logging.error("ACCESS_PIN not found in environment variables.")
        return func.HttpResponse(
            json.dumps({"error": "Server configuration error: ACCESS_PIN not set"}),
            status_code=500,
            mimetype="application/json"
        )

    client_pin = req.headers.get("x-access-pin")

    if client_pin == env_pin:
        return None

    logging.warning(f"Invalid PIN attempt. Provided: {client_pin}")
    return func.HttpResponse(
         json.dumps({"error": "Unauthorized: Invalid Access PIN"}),
         status_code=401,
         mimetype="application/json"
    )
