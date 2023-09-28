#db_connection.py

import pymongo

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "test"
MONGO_COLLECTION_NAME = "Data_KTP"

def create_mongo_connection():
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI)
        mongo_db = mongo_client[MONGO_DB_NAME]
        mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
        return mongo_collection
    except Exception as e:
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")
