import logging
import os
from pathlib import Path

from amadeus import Client
from dotenv import load_dotenv
import yaml

logger = logging.getLogger(__name__)

load_dotenv()
CLIENT_ID = os.getenv("AMADEUS_CLIENT_ID")
CLIENT_SECRET = os.getenv("AMADEUS_CLIENT_SECRET")
HOSTNAME = os.getenv("AMADEUS_HOSTNAME", "test")


def load_users() -> list[dict]:
    users_path = Path(__file__).parent.parent / "users.yml"
    with open(users_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("users", [])


def _parse_duration(duration: str) -> int:
    """Parses ISO 8601 duration (e.g. PT2H30M) to minutes."""
    duration = duration.replace("PT", "")
    hours = int(duration.split("H")[0]) if "H" in duration else 0
    minutes = int(duration.split("H")[-1].replace("M", "")) if "M" in duration else 0
    return hours * 60 + minutes


def _filter_by_duration(offers: list, max_hours: int) -> list:
    max_minutes = max_hours * 60
    filtered = []
    for offer in offers:
        total_minutes = sum(
            _parse_duration(segment["duration"])
            for itinerary in offer["itineraries"]
            for segment in itinerary["segments"]
        )
        if total_minutes <= max_minutes:
            filtered.append(offer)
    return filtered


def _filter_by_baggage(offers: list) -> list:
    filtered = []
    for offer in offers:
        has_baggage = all(
            any(
                segment.get("includedCheckedBags", {}).get("quantity", 0) > 0
                for segment in traveler.get("fareDetailsBySegment", [])
            )
            for traveler in offer.get("travelerPricings", [])
        )
        if has_baggage:
            filtered.append(offer)
    return filtered


def fetch_flight_offers(client: Client, trip: dict) -> dict | None:
    origin = trip["origin"]
    destination = trip["destination"]
    departure_date = trip["departure_date"]
    return_date = trip.get("return_date")
    max_price = trip.get("max_price")
    currency = trip.get("currency", "EUR")
    adults = trip.get("adults", 1)
    children = trip.get("children", 0)
    infants = trip.get("infants", 0)

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": departure_date,
        "returnDate": return_date,
        "adults": adults,
        "currencyCode": currency,
    }

    # optional parameters
    if children:
        params["children"] = children

    if infants:
        params["infants"] = infants

    if trip.get("travel_class"):
        params["travelClass"] = trip["travel_class"]

    if trip.get("airline") and trip.get("excluded_airlines"):
        logger.warning(
            f"Trip {origin} -> {destination}: 'airline' and 'excluded_airlines' "
            f"cannot be used together. Ignoring 'excluded_airlines'."
        )

    if trip.get("airline"):
        params["includedAirlineCodes"] = trip["airline"]
    elif trip.get("excluded_airlines"):
        params["excludedAirlineCodes"] = ",".join(trip["excluded_airlines"])

    if trip.get("max_stops") == 0:
        params["nonStop"] = True

    try:
        response = client.shopping.flight_offers_search.get(**params)
        offers = response.data

        if not offers:
            logger.info(f"No offers found for {origin} -> {destination}")
            return None

        # post-response filters
        if trip.get("max_duration_hours"):
            offers = _filter_by_duration(offers, trip["max_duration_hours"])

        if trip.get("included_baggage"):
            offers = _filter_by_baggage(offers)

        if not offers:
            logger.info(
                f"No offers found after filtering for {origin} -> {destination}"
            )
            return None

        best_price = float(offers[0]["price"]["total"])

        # adjust price check per person if set
        if trip.get("max_price_per_person"):
            total_passengers = adults + children + infants
            comparable_price = best_price / total_passengers
        else:
            comparable_price = best_price

        carrier = (
            trip.get("airline")
            or offers[0]["itineraries"][0]["segments"][0]["carrierCode"]
        )
        logger.info(
            f"Best price for {origin} -> {destination}: {best_price} {currency} ({carrier})"
        )

        return {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "best_price": best_price,
            "comparable_price": comparable_price,
            "max_price": max_price,
            "currency": currency,
            "airline": carrier,
        }

    except Exception as e:
        logger.error(f"Error fetching flight offers for {origin} -> {destination}: {e}")
        return None


def fetch_all_trips() -> list[dict]:
    users = load_users()
    amadeus = Client(
        client_id=CLIENT_ID, client_secret=CLIENT_SECRET, hostname=HOSTNAME
    )

    results = []
    for user in users:
        user_result = {
            "name": user.get("name"),
            "email": user.get("email"),
            "trips": [],
        }
        for trip in user.get("trips", []):
            offer = fetch_flight_offers(amadeus, trip)
            if offer:
                user_result["trips"].append(offer)

        results.append(user_result)

    return results


def main():
    results = fetch_all_trips()
    for user in results:
        logger.info(f"User: {user['name']} ({user['email']})")
        for trip in user["trips"]:
            logger.info(
                f"  Trip: {trip['origin']} -> {trip['destination']} on {trip['departure_date']} "
                f"- Best Price: {trip['best_price']} {trip['currency']} "
                f"(Max: {trip['max_price']} {trip['currency']}) "
                f"- Airline: {trip['airline']}"
            )


if __name__ == "__main__":
    main()
