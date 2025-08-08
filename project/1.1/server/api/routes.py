from flask import Blueprint, jsonify, session
from pymongo import MongoClient
from groups import GROUPS

api_blueprint = Blueprint("api", __name__)

client = MongoClient("mongodb://localhost:27017/")
db = client["schnorr_auth_app"]

# /api/handshake

@api_blueprint.route("/handshake", methods=["GET"])
def handshake():
    
    group = "modp-1536"
    
    return jsonify({"group-id": group}), 200

@api_blueprint.route("/status", methods=["GET"])
def status():
    return jsonify({"status": "OK", "service": "Flask API"})
