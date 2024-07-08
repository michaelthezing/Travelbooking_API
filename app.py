from flask import Flask, request, jsonify
from datetime import datetime
import uuid
import requests
import stripe
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# Load environment variables from .env file
load_dotenv()

# MongoDB Configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['travel_booking_db']
users_collection = db['users']
bookings_collection = db['bookings']
payments_collection = db['payments']

# Amadeus API credentials
AMADEUS_API_KEY = os.getenv('AMADEUS_API_KEY')
AMADEUS_API_SECRET = os.getenv('AMADEUS_API_SECRET')
AMADEUS_AUTH_URL = 'https://test.api.amadeus.com/v1/security/oauth2/token'
AMADEUS_FLIGHT_OFFERS_URL = 'https://test.api.amadeus.com/v2/shopping/flight-offers'

# Stripe API credentials
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

def get_amadeus_token():
    auth_response = requests.post(AMADEUS_AUTH_URL, data={
        'grant_type': 'client_credentials',
        'client_id': AMADEUS_API_KEY,
        'client_secret': AMADEUS_API_SECRET
    })
    auth_response.raise_for_status()
    return auth_response.json()['access_token']

def validate_flight_offer(origin, destination, departure_date):
    # Extract the date portion from the datetime string
    departure_date = departure_date.split("T")[0]
    
    access_token = get_amadeus_token()
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.get(AMADEUS_FLIGHT_OFFERS_URL, headers=headers, params={
        'originLocationCode': origin,
        'destinationLocationCode': destination,
        'departureDate': departure_date,
        'adults': 1
    })
    response.raise_for_status()
    return response.json()


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
    user_id = data.get("user_id")
    flight_offer_id = data.get("flight_offer_id")
    origin = data.get("origin")
    destination = data.get("destination")
    departure_date = data.get("start_date").split("T")[0]
    if not users_collection.find_one({"_id": user_id}):
        return jsonify({"message": "User not found"}), 404

    # Validate flight offer
    try:
        flight_offers = validate_flight_offer(origin, destination, departure_date)
        valid_offer = None
        for offer in flight_offers['data']:
            if offer['id'] == flight_offer_id:
                valid_offer = offer
                break
        if not valid_offer:
            return jsonify({"message": "No valid flight offer found for the provided ID"}), 400
    except Exception as e:
        return jsonify({"message": "Error validating flight offer", "error": str(e)}), 400
    
    new_booking = {
        "_id": booking_id,
        "user_id": user_id,
        "flight_offer_id": flight_offer_id,
        "origin": origin,
        "destination": destination,
        "departure_date": departure_date,
        "booking_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "flight_details": valid_offer
    }
    bookings_collection.insert_one(new_booking)
    return jsonify({"message": "Trip booked successfully", "booking_id": booking_id}), 201


@app.route("/get-bookings/<user_id>", methods=["GET"])
def get_bookings(user_id):
    if not users_collection.find_one({"_id": user_id}):
        return jsonify({"message": "User not found"}), 404
    
    user_bookings = bookings_collection.find({"user_id": user_id})
    bookings_list = [{
        "booking_id": booking["_id"],
        "user_id": booking["user_id"],
        "origin": booking["origin"],
        "destination": booking["destination"],
        "start_date": booking["start_date"],
        "end_date": booking["end_date"],
        "booking_date": booking["booking_date"]
    } for booking in user_bookings]
    return jsonify(bookings_list), 200

@app.route("/cancel-booking/<booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    result = bookings_collection.delete_one({"_id": booking_id})
    if result.deleted_count == 0:
        return jsonify({"message": "Booking not found"}), 404
    
    return jsonify({"message": "Booking cancelled successfully"}), 200

@app.route("/search-bookings", methods=["GET"])
def search_bookings():
    destination = request.args.get("destination")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    
    query = {}
    if destination:
        query["destination"] = destination
    if start_date:
        query["start_date"] = {"$gte": start_date}
    if end_date:
        query["end_date"] = {"$lte": end_date}
    
    filtered_bookings = bookings_collection.find(query)
    bookings_list = [{
        "booking_id": booking["_id"],
        "user_id": booking["user_id"],
        "origin": booking["origin"],
        "destination": booking["destination"],
        "start_date": booking["start_date"],
        "end_date": booking["end_date"],
        "booking_date": booking["booking_date"]
    } for booking in filtered_bookings]
    return jsonify(bookings_list), 200

@app.route("/update-booking/<booking_id>", methods=["PUT"])
def update_booking(booking_id):
    booking = bookings_collection.find_one({"_id": booking_id})
    if not booking:
        return jsonify({"message": "Booking not found"}), 404

    data = request.get_json()
    update_fields = {
        "origin": data.get("origin", booking["origin"]),
        "destination": data.get("destination", booking["destination"]),
        "start_date": data.get("start_date", booking["start_date"]),
        "end_date": data.get("end_date", booking["end_date"])
    }
    bookings_collection.update_one({"_id": booking_id}, {"$set": update_fields})
    
    updated_booking = bookings_collection.find_one({"_id": booking_id})
    return jsonify({"message": "Booking updated successfully", "booking": {
        "booking_id": updated_booking["_id"],
        "user_id": updated_booking["user_id"],
        "origin": updated_booking["origin"],
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
    booking = bookings_collection.find_one({"_id": booking_id})
    if not booking:
        return jsonify({"message": "Booking not found"}), 404
    
    # Get the price of the ticket from the flight details
    ticket_price = booking["flight_details"]["price"]["total"]
    ticket_price = float(ticket_price)

    # Check if the amount is enough to cover the ticket price
    if amount < ticket_price:
        return jsonify({"message": "Amount is not enough to cover the ticket price"}), 400

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



@app.route("/search-flights", methods=["GET"])
def search_flights():
    origin = request.args.get("origin")
    destination = request.args.get("destination")
    departure_date = request.args.get("departure_date")
    
    if not origin or not destination or not departure_date:
        return jsonify({"message": "Missing required parameters"}), 400
    
    # Get Amadeus Access Token
    try:
        auth_response = requests.post(AMADEUS_AUTH_URL, data={
            'grant_type': 'client_credentials',
            'client_id': AMADEUS_API_KEY,
            'client_secret': AMADEUS_API_SECRET
        })
        auth_response.raise_for_status()
        access_token = auth_response.json()['access_token']
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Failed to get Amadeus access token", "error": str(e)}), 500
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        flight_response = requests.get(AMADEUS_FLIGHT_OFFERS_URL, headers=headers, params={
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'adults': 1
        })
        flight_response.raise_for_status()
        flight_offers = flight_response.json()
    except requests.exceptions.RequestException as e:
        return jsonify({"message": "Failed to get flight offers from Amadeus", "error": str(e)}), 500
    
    return jsonify(flight_offers), 200






if __name__ == "__main__":
    app.run(debug=True)
