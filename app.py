from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import requests
import stripe
from pymongo import MongoClient

app = Flask(__name__)

# Simulated database
users = {}


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    user_id = str(uuid.uuid4())
    users[user_id] = {
        "user_id": user_id,
        "name": data.get("name"),
        "email": data.get("email"),
        "password": data.get("password")  
    }
    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    for user_id, user in users.items():
        if user["email"] == email and user["password"] == password:
            return jsonify({"message": "Login successful", "user_id": user_id}), 200
    return jsonify({"message": "Invalid credentials"}), 401


if __name__ == "__main__":
    app.run(debug=True)
