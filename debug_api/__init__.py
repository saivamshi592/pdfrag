import logging
import azure.functions as func
import json
import os
import sys

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Debug API: Starting diagnostics...')
    
    results = {
        "status": "alive",
        "imports": {},
        "env_vars": {},
        "python_version": sys.version
    }

    # 1. Test Imports (To check if deployment installed requirements.txt)
    try:
        import pymongo
        results["imports"]["pymongo"] = f"Success ({pymongo.version})"
    except ImportError as e:
        results["imports"]["pymongo"] = f"Failed: {str(e)}"

    try:
        import pypdf
        results["imports"]["pypdf"] = "Success"
    except ImportError as e:
        results["imports"]["pypdf"] = f"Failed: {str(e)}"

    try:
        import openai
        results["imports"]["openai"] = "Success"
    except ImportError as e:
        results["imports"]["openai"] = f"Failed: {str(e)}"

    # 2. Check Key Env Vars (Masked)
    keys_to_check = [
        "MONGO_URI", 
        "AZURE_OPENAI_API_KEY", 
        "AZURE_OPENAI_ENDPOINT",
        "AzureWebJobsStorage",
        "ACCESS_PIN"
    ]
    for k in keys_to_check:
        val = os.getenv(k)
        if val:
            results["env_vars"][k] = "Present (Length: " + str(len(val)) + ")"
        else:
            results["env_vars"][k] = "MISSING"

    logging.info(f"Debug Results: {json.dumps(results)}")

    return func.HttpResponse(
        json.dumps(results, indent=2),
        status_code=200,
        mimetype="application/json"
    )
