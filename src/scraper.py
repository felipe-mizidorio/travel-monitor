import logging
from datetime import datetime, time as dt_time
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


def _parse_flight_time(time_str: str) -> dt_time | None:
    """Parses a flight time string such as '1:25 PM on Fri, May 8' to a time object."""
    if not time_str:
        return None
    # Normalize Unicode whitespace (e.g. narrow no-break space used by Google Flights)
    normalized = re.sub(r"\s+", " ", time_str).strip()
    # Extract 12h time (e.g. "1:25 PM") ignoring trailing date info
    match = re.search(r"\d{1,2}:\d{2}\s*[AP]M", normalized, re.IGNORECASE)
    if match:
        try:
            return datetime.strptime(re.sub(r"\s+", " ", match.group()).strip(), "%I:%M %p").time()
        except ValueError:
            pass
    # Fallback: extract 24h time (e.g. "13:25")
    match = re.search(r"\b\d{1,2}:\d{2}\b", normalized)
    if match:
        try:
            return datetime.strptime(match.group(), "%H:%M").time()
        except ValueError:
            pass
    return None


def _in_time_range(flight_time_str: str, from_str: str | None, to_str: str | None) -> bool:
    """Returns True if flight_time_str satisfies the given bounds (HH:MM 24h format).

    Either bound may be omitted for open-ended filtering.
    """
    flight_time = _parse_flight_time(flight_time_str)
    if flight_time is None:
        return True  # don't filter out if time is unparseable
    if from_str and flight_time < datetime.strptime(from_str, "%H:%M").time():
        return False
    if to_str and flight_time > datetime.strptime(to_str, "%H:%M").time():
        return False
    return True


def _fetch_best_flight(
    *,
    origin: str,
    destination: str,
    date: str,
    seat: str,
    passengers: Passengers,
    currency: str,
    max_stops: int | None = None,
    max_duration_hours: float | None = None,
    time_from: str | None = None,
    time_to: str | None = None,
) -> dict | None:
    """Fetches the cheapest one-way flight matching the filters.

    Returns a dict with flight details or None if no flights match.
    """
    tfs = create_filter(
        flight_data=[FlightData(date=date, from_airport=origin, to_airport=destination)],
        trip="one-way",
        seat=seat,
        passengers=passengers,
    )

    result = get_flights_from_filter(tfs, currency=currency, mode="local")
    flights = result.flights

    if not flights:
        logger.info(f"No flights found for {origin} -> {destination} on {date}")
        return None

    if max_stops == 0:
        flights = [f for f in flights if f.stops == 0]

    if max_duration_hours:
        max_minutes = max_duration_hours * 60
        flights = [f for f in flights if _parse_duration(f.duration) <= max_minutes]

    if time_from or time_to:
        flights = [f for f in flights if _in_time_range(f.departure, time_from, time_to)]

    if not flights:
        logger.info(
            f"No flights found for {origin} -> {destination} on {date} after applying filters"
        )
        return None

    best = min(flights, key=lambda f: _parse_price(f.price))
    logger.info(
        f"  → {origin} → {destination} on {date}: {best.departure} → {best.arrival} "
        f"({best.duration}, {best.stops} stop(s)) at {best.price} with {best.name}"
    )
    return {
        "price": _parse_price(best.price),
        "airline": best.name,
        "departure_time": best.departure,
        "arrival_time": best.arrival,
        "duration": best.duration,
        "stops": best.stops,
    }


def fetch_flight_offers(trip: dict) -> dict | None:
    origin = str(trip["origin"])
    destination = str(trip["destination"])
    departure_date = str(trip["departure_date"])
    return_date = str(trip.get("return_date")) if trip.get("return_date") else None
    max_price = trip.get("max_price")
    currency = trip.get("currency", "EUR")
    adults = int(trip.get("adults", 1))
    children = int(trip.get("children", 0))
    infants = int(trip.get("infants", 0))

    SeatType: TypeAlias = Literal["economy", "premium-economy", "business", "first"]

    seat_map: dict[str, SeatType] = {
        "ECONOMY": "economy",
        "PREMIUM_ECONOMY": "premium-economy",
        "BUSINESS": "business",
        "FIRST": "first",
    }
    seat: SeatType = seat_map.get(trip.get("travel_class", "ECONOMY"), "economy")

    passengers = Passengers(
        adults=adults,
        children=children,
        infants_in_seat=infants,
    )

    max_stops = trip.get("max_stops")
    max_duration_hours = trip.get("max_duration_hours")

    try:
        outbound = _fetch_best_flight(
            origin=origin,
            destination=destination,
            date=departure_date,
            seat=seat,
            passengers=passengers,
            currency=currency,
            max_stops=max_stops,
            max_duration_hours=max_duration_hours,
            time_from=trip.get("departure_time_from"),
            time_to=trip.get("departure_time_to"),
        )

        if outbound is None:
            return None

        if return_date:
            inbound = _fetch_best_flight(
                origin=destination,
                destination=origin,
                date=return_date,
                seat=seat,
                passengers=passengers,
                currency=currency,
                max_stops=max_stops,
                max_duration_hours=max_duration_hours,
                time_from=trip.get("return_time_from"),
                time_to=trip.get("return_time_to"),
            )

            if inbound is None:
                return None

            best_price = outbound["price"] + inbound["price"]
            carrier = trip.get("airline") or f"{outbound['airline']} / {inbound['airline']}"
        else:
            inbound = None
            best_price = outbound["price"]
            carrier = trip.get("airline") or outbound["airline"]

        if trip.get("max_price_per_person"):
            total_passengers = adults + children + infants
            comparable_price = best_price / total_passengers
        else:
            comparable_price = best_price

        logger.info(
            f"Best flight for {origin} -> {destination} on {departure_date}: {best_price} {currency} with {carrier}"
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
            "outbound": outbound,
            "inbound": inbound,
        }

    except Exception as e:
        import traceback

        logger.error(
            f"Error fetching flights for {origin} -> {destination} on {departure_date}: {e}\n{traceback.format_exc()}"
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
