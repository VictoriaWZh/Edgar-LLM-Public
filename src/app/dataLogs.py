import json
from datetime import datetime
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("MONGO_URI not set in environment variables.")

if "?" in mongo_uri:
    mongo_uri += "&ssl=true&tls=true"
else:
    mongo_uri += "?ssl=true&tls=true"

try:
    client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=True)
    print("Connected to MongoDB successfully.")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")
    raise

class DataLogs:
    @staticmethod
    def write_json(record):
        log_file = "chatbot_logs.json"
        
        def serialize_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        try:
            if os.path.exists(log_file) and os.path.getsize(log_file) > 0:
                with open(log_file, "r", encoding="utf-8") as file:
                    data = json.load(file)
            else:
                data = []
            
            data.append(record)
            with open(log_file, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, default=serialize_datetime)
            print("Record successfully logged.")
        except Exception as e:
            print(f"Error logging record: {e}")
    
    @staticmethod
    def write_mongodb(record):
        try:
            db_logs = client['chatbot_logs']
            logs_collection = db_logs['logs']
            logs_collection.insert_one(record)
            print("Record successfully logged to MongoDB.")
        except Exception as e:
            print(f"Error logging record to MongoDB: {e}")
