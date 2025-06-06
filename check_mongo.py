#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pymongo import MongoClient
import json
from bson import json_util

try:
    # MongoDB connection
    client = MongoClient('mongodb://root:otlehjoq543680@46.101.121.75:27017/admin')
    
    # Switch to Pivo database
    db = client.Pivo

    # Check collections
    collections = db.list_collection_names()
    print("Collections in Pivo database:")
    print(collections)

    if 'catalog' in collections:
        # Check documents in catalog collection
        print("\nFirst 3 documents from catalog collection:")
        cursor = db.catalog.find().limit(3)
        for doc in cursor:
            print(json.loads(json_util.dumps(doc)))

        # Count documents
        count = db.catalog.count_documents({})
        print(f"\nTotal documents in collection: {count}")

        # Check document structure
        print("\nAll unique fields in collection:")
        all_fields = set()
        for doc in db.catalog.find():
            all_fields.update(doc.keys())
        print(sorted(list(all_fields)))
    else:
        print("Collection 'catalog' not found!")

except Exception as e:
    print(f"MongoDB Error: {str(e)}")
finally:
    if 'client' in locals():
        client.close()
