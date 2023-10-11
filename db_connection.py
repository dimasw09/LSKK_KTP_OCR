# db_connection.py
import pymongo
import logging

MONGO_URI = "mongodb://localhost:27017/"
MONGO_DB_NAME = "admin"
MONGO_COLLECTION_NAME = "ktp"

def create_mongo_connection():
    try:
        logging.info("Connecting to MongoDB...")
        mongo_client = pymongo.MongoClient(MONGO_URI)
        logging.info("Connected to MongoDB.")
        mongo_db = mongo_client[MONGO_DB_NAME]
        mongo_collection = mongo_db[MONGO_COLLECTION_NAME]
        return mongo_collection
    except Exception as e:
        logging.error(f"Failed to connect to MongoDB: {str(e)}")
        raise Exception(f"Failed to connect to MongoDB: {str(e)}")
