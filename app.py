from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import requests
import stripe
from pymongo import MongoClient
from dotenv import load_dotenv

import os

app = Flask(__name__)

client = MongoClient('mongodb://localhost:27017/')
db = client['TravelBooking']
users_collection = db['users']
bookings_collection = db['bookings']
payments_collection = db['payments']

AMADEUS_AUTH_URL = 'https://test.api.amadeus.com/v1/security/oauth2/token'
AMADEUS_FLIGHT_OFFERS_URL = 'https://test.api.amadeus.com/v2/shopping/flight-offers'
load_dotenv()

AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
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
@app.route("/update-booking/booking_id", methods = ["PUT"])
def update_booking(booking_id):
    booking = bookings_collection.find_one({"_id": booking_id})
    if not booking:
        return jsonify({"message": "Booking not found"}), 404
    data = request.get_json()
    update_fields = {
        "destination": data.get("destination", booking["destination"]),
        "start_date": data.get("start_date", booking["start_date"]),
        "end_date": data.get("end_date", booking["end_date"])
    }
    bookings_collection.update_one({"_id": booking_id}, {"$set": update_fields})
    
    updated_booking = bookings_collection.find_one({"_id": booking_id})
    return jsonify({"message": "Booking updated successfully", "booking": {
        "booking_id": updated_booking["_id"],
        "user_id": updated_booking["user_id"],
        "destination": updated_booking["destination"],
        "start_date": updated_booking["start_date"],
        "end_date": updated_booking["end_date"],
        "booking_date": updated_booking["booking_date"]
    }}), 200

@app.route("/make-payment", methods=["POST"])
def make_payment():
    data = request.get_json()
    payment_id = str(uuid.uuid4())
    user_id = data.get("user_id")
    booking_id = data.get("booking_id")
    amount = data.get("amount")
    
    if not users_collection.find_one({"_id": user_id}):
        return jsonify({"message": "User not found"}), 404
    if not bookings_collection.find_one({"_id": booking_id}):
        return jsonify({"message": "Booking not found"}), 404
    
    # Create Stripe Payment Intent
    intent = stripe.PaymentIntent.create(
        amount=int(amount * 100),  # amount in cents
        currency='usd',
        metadata={'integration_check': 'accept_a_payment'},
    )
    
    new_payment = {
        "_id": payment_id,
        "user_id": user_id,
        "booking_id": booking_id,
        "amount": amount,
        "payment_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stripe_payment_intent_id": intent['id']
    }
    payments_collection.insert_one(new_payment)
    return jsonify({"message": "Payment successful", "payment_id": payment_id, "client_secret": intent['client_secret']}), 201


def get_amadeus_token():
    response = requests.post(AMADEUS_AUTH_URL, data={
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    })
    response.raise_for_status()
    return response.json()['access_token']


@app.route("/search-flights", methods=["GET"])
def search_flights():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    departure_date = request.args.get("departure_date")
    return_date = request.args.get("return_date")
    adults = request.args.get("adults", 1)
    
    # Ensure all required parameters are provided
    if not origin or not destination or not departure_date or not return_date:
        return jsonify({"message": "Missing required parameters"}), 400
    
    try:
        token = get_amadeus_token()
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error fetching token", "error": str(e)}), 500

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    params = {
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'returnDate': return_date,
        'adults': adults
    }

    # Log the request details for debugging
    print(f"Request URL: {AMADEUS_FLIGHT_OFFERS_URL}")
    print(f"Headers: {headers}")
    print(f"Params: {params}")

    try:
        response = requests.get(AMADEUS_FLIGHT_OFFERS_URL, headers=headers, params=params)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Error fetching flight offers", "error": str(e), "response": response.text}), 400
    
    return jsonify(response.json())


if __name__ == "__main__":
    app.run(debug=True)
