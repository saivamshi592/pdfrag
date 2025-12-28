import logging
import azure.functions as func
import json
from services.mongo_store import mongo_store

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('List PDFs API triggered.')

    from services.auth import validate_pin
    if auth_error := validate_pin(req):
        return auth_error

    try:
        type_param = req.params.get('type')
        
        # Mode 1: List Categories
        if type_param == 'categories':
            cats = mongo_store.get_all_categories()
            return func.HttpResponse(
                json.dumps({"categories": sorted(list(cats))}),
                status_code=200,
                mimetype="application/json"
            )

        # Mode 2: List PDFs in Category
        category = req.params.get('category')
        if not category:
            return func.HttpResponse(
                json.dumps({"error": "Missing category param"}),
                status_code=400,
                mimetype="application/json"
            )

        # FIX: Directly query collection instead of calling non-existent list_pdfs method
        pdfs = []
        collection = mongo_store.collection
        
        if collection is not None:
            try:
                # Retrieve unique PDF names for the given category
                distinct_pdfs = collection.distinct("pdf_name", {"category": category})
                # Filter out any None/Empty values and sort
                pdfs = sorted([p for p in distinct_pdfs if p])
            except Exception as db_err:
                logging.error(f"Error querying MongoDB for PDFs: {db_err}")
                # Fallback to empty list gracefully
                pdfs = []
        else:
            logging.warning("MongoDB collection not available for listing PDFs.")
            pdfs = []
        
        return func.HttpResponse(
            json.dumps({"category": category, "pdfs": pdfs}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("List API failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
