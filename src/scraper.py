import logging
from pathlib import Path
import re
from typing import Literal, TypeAlias

from fast_flights import FlightData, Passengers, create_filter, get_flights_from_filter
from dotenv import load_dotenv
import yaml

logger = logging.getLogger(__name__)

load_dotenv()


def load_users() -> list[dict]:
    users_path = Path(__file__).parent.parent / "users.yml"
    with open(users_path, "r") as f:
        data = yaml.safe_load(f)
    return data.get("users", [])


def _parse_price(price_str: str) -> float:
    """Parses price string to float."""
    cleaned = re.sub(r"[^\d.,]", "", price_str).replace(",", "")
    return float(cleaned)


def _parse_duration(duration_str: str) -> int:
    """Parses a duration string to minutes."""
    hours = re.search(r"(\d+)\s*hr", duration_str)
    minutes = re.search(r"(\d+)\s*min", duration_str)
    total = 0
    if hours:
        total += int(hours.group(1)) * 60
    if minutes:
        total += int(minutes.group(1))
    return total


def fetch_flight_offers(trip: dict) -> dict | None:
    origin = trip["origin"]
    destination = trip["destination"]
    departure_date = trip["departure_date"]
    return_date = trip.get("return_date")
    max_price = trip.get("max_price")
    currency = trip.get("currency", "EUR")
    adults = trip.get("adults", 1)
    children = trip.get("children", 0)
    infants = trip.get("infants", 0)

    SeatType: TypeAlias = Literal["economy", "premium-economy", "business", "first"]
    TripType: TypeAlias = Literal["round-trip", "one-way", "multi-city"]

    seat_map: dict[str, SeatType] = {
        "ECONOMY": "economy",
        "PREMIUM_ECONOMY": "premium-economy",
        "BUSINESS": "business",
        "FIRST": "first",
    }
    seat: SeatType = seat_map.get(trip.get("travel_class", "ECONOMY"), "economy")

    flight_data = [
        FlightData(date=departure_date, from_airport=origin, to_airport=destination)
    ]
    if return_date:
        flight_data.append(
            FlightData(date=return_date, from_airport=destination, to_airport=origin)
        )

    trip_type: TripType = "round-trip" if return_date else "one-way"

    try:
        tfs = create_filter(
            flight_data=flight_data,
            trip=trip_type,
            seat=seat,
            passengers=Passengers(
                adults=adults,
                children=children,
                infants_in_seat=infants,
            ),
        )

        result = get_flights_from_filter(
            tfs,
            currency=currency,
            mode="local",
        )

        flights = result.flights
        if not flights:
            logger.info(
                f"No flights found for {origin} -> {destination} on {departure_date}"
            )
            return None

        if trip.get("max_stops") == 0:
            flights = [f for f in flights if f.stops == 0]

        if trip.get("max_duration_hours"):
            max_minutes = trip["max_duration_hours"] * 60
            flights = [f for f in flights if _parse_duration(f.duration) <= max_minutes]

        if not flights:
            logger.info(
                f"No flights found for {origin} -> {destination} on {departure_date} after applying filters"
            )
            return None

        best = min(flights, key=lambda f: _parse_price(f.price))
        best_price = _parse_price(best.price)

        if trip.get("max_price_per_person"):
            total_passengers = adults + children + infants
            comparable_price = best_price / total_passengers
        else:
            comparable_price = best_price

        carrier = trip.get("airline") or best.name
        logger.info(
            f"Best flight for {origin} -> {destination} on {departure_date}: {best.price} {currency} with {carrier}"
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
        logger.error(
            f"Error fetching flights for {origin} -> {destination} on {departure_date}: {e}"
        )
        return None


def fetch_all_trips() -> list[dict]:
    users = load_users()
    results = []
    for user in users:
        user_result: dict = {
            "name": user.get("name"),
            "email": user.get("email"),
            "trips": [],
        }
        for trip in user.get("trips", []):
            offer = fetch_flight_offers(trip)
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
