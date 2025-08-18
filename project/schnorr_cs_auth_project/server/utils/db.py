from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["schnorr_auth_app"]
