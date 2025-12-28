import os
import json
import dns.resolver
from pymongo import MongoClient

# 🔹 DNS PATCH (IMPORTANT)
resolver = dns.resolver.Resolver()
resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
dns.resolver.default_resolver = resolver

# 🔹 Load env vars from local.settings.json
with open("local.settings.json") as f:
    settings_json = json.load(f)
    values = settings_json.get("Values", {})
    for k, v in values.items():
        os.environ[k] = v

from config.settings import settings

print("Connecting to Mongo Cosmos DB...")

client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=10000)

db = client[settings.MONGO_DB_NAME]
coll = db[settings.MONGO_COLLECTION_NAME]

count = coll.count_documents({})
print("✅ Total documents in collection:", count)

doc = coll.find_one()
print("\n✅ Sample document:")
print(doc)
