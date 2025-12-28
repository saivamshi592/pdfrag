import logging
import azure.functions as func
import json
from services.mongo_store import mongo_store
from services.auth import validate_pin

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Categories API triggered")

    # PIN Authentication
    if auth_error := validate_pin(req):
        return auth_error

    try:
        cats = mongo_store.get_all_categories()
        return func.HttpResponse(
            json.dumps({"categories": sorted(list(cats))}),
            status_code=200,
            mimetype="application/json"
        )
    except Exception as e:
        logging.exception("Categories API failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
