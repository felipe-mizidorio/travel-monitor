import logging
import os

from amadeus import Client
from dotenv import load_dotenv
import yaml

logger = logging.getLogger(__name__)

load_dotenv()
client_id = os.getenv("AMADEUS_CLIENT_ID")
client_secret = os.getenv("AMADEUS_CLIENT_SECRET")

def load_config() -> dict:
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)
    
def fetch_flight_offers(client: Client, trip: dict, preferences: dict) -> list | None:
    origin = trip["origin"]
    destination = trip["destination"]
    departure_date = trip["departure_date"]
    return_date = trip.get("return_date")
    max_price = trip.get("max_price")
    currency = preferences.get("currency")
    adults = preferences.get("adults", 1)

    try:
        response = client.shopping.flight_offers_search.get(
            originLocationCode=origin,
            destinationLocationCode=destination,
            departureDate=departure_date,
            returnDate=return_date,
            adults=adults,
            currencyCode=currency,
        )
        offers = response.data

        if not offers:
            logger.info(f"No offers found for {origin} -> {destination}")
            return None

        best_price = float(offers[0]["price"]["total"])
        logger.info(f"Best price for {origin} -> {destination}: {best_price} {currency}")

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "best_price": best_price,
            "max_price": max_price,
            "currency": currency,
        }

    except Exception as e:
        logger.error(f"Error fetching flight offers for {origin} -> {destination}: {e}")
        return None
    
def fetch_all_trips() -> list[dict]:
    config = load_config()
    amadeus = Client(client_id=client_id, client_secret=client_secret)
    trips = config.get("trips", [])
    preferences = config.get("preferences", {})
    
    results = []
    for trip in trips:
        offer = fetch_flight_offers(amadeus, trip, preferences)
        if offer:
            results.append(offer)
    
    return results

def main():
    results = fetch_all_trips()
    for result in results:
        logger.info(f"Trip: {result['origin']} -> {result['destination']} on {result['departure_date']} - Best Price: {result['best_price']} {result['currency']} (Max Price: {result['max_price']} {result['currency']})")

if __name__ == "__main__":
    main()
