# db_connection.py
import pymongo
import logging


MONGO_URI = "mongodb://magangitg:bWFnYW5naXRn@database2.pptik.id:27017/?authMechanism=DEFAULT&authSource=magangitg"
MONGO_DB_NAME = "magangitg"
MONGO_COLLECTION_NAME = "ktp_ocr"

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
