import logging
import azure.functions as func
import json
from services.mongo_store import mongo_store

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('List PDFs API triggered.')

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

        pdfs = mongo_store.list_pdfs(category)
        
        return func.HttpResponse(
            json.dumps({"category": category, "pdfs": pdfs}),
            status_code=200,
            mimetype="application/json"
        )

    except Exception as e:
        logging.exception("List failed")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
