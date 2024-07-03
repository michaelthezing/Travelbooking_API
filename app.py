from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import requests
import stripe
from pymongo import MongoClient

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['TravelBooking']
users_collection = db['users']
bookings_collection = db['bookings']
payments_collection = db['payments']

AMADEUS_API_KEY = 'API_KEY'
AMADEUS_API_SECRET = 'API_SECRET'

stripe.api_key = 'YOUR_STRIPE_SECRET_KEY'
# Simulated database
users = {}


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    user_id = str(uuid.uuid4())
    new_user = {
        "_id": user_id,
        "name": data.get("name"),
        "email": data.get("email"),
        "password": data.get("password")
    }
    users_collection.insert_one(new_user)
    return jsonify({"message": "User registered successfully", "user_id": user_id}), 201

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = users_collection.find_one({"email": email, "password": password})
    if user:
        return jsonify({"message": "Login successful", "user_id": user["_id"]}), 200
    return jsonify({"message": "Invalid credentials"}), 401


@app.route("/book-trip", methods=["POST"])
def book_trip():
    data = request.get_json()
    booking_id = str(uuid.uuid4())
    user_name = data.get("user_name")
    
    user = users_collection.find_one({"name": user_name})
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    user_id = user["_id"]
    
    new_booking = {
        "_id": booking_id,
        "user_id": user_id,
        "destination": data.get("destination"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "booking_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    bookings_collection.insert_one(new_booking)
    return jsonify({"message": "Trip booked successfully", "booking_id": booking_id}), 201


@app.route("/cancel-booking/<booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    result = bookings_collection.delete_one({"_id": booking_id})
    if result.deleted_count == 0:
         return jsonify({"message": "Booking not found"}), 404
    
    return jsonify({"message": "Booking cancelled successfully"}), 200

if __name__ == "__main__":
    app.run(debug=True)
