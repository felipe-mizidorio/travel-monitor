from src.notifier import filter_deals


MOCK_TRIP = {
    "origin": "OPO",
    "destination": "BCN",
    "departure_date": "2026-06-01",
    "return_date": "2026-06-15",
    "currency": "EUR",
    "airline": "IB",
    "max_price": 500,
}


def test_filter_deals_finds_deal():
    trips = [{**MOCK_TRIP, "best_price": 300.0, "comparable_price": 300.0}]
    deals = filter_deals(trips)
    assert len(deals) == 1


def test_filter_deals_no_deal():
    trips = [{**MOCK_TRIP, "best_price": 600.0, "comparable_price": 600.0}]
    deals = filter_deals(trips)
    assert len(deals) == 0


def test_filter_deals_exact_max_price():
    trips = [{**MOCK_TRIP, "best_price": 500.0, "comparable_price": 500.0}]
    deals = filter_deals(trips)
    assert len(deals) == 1


def test_filter_deals_multiple_trips():
    trips = [
        {**MOCK_TRIP, "best_price": 300.0, "comparable_price": 300.0},
        {**MOCK_TRIP, "best_price": 600.0, "comparable_price": 600.0},
        {**MOCK_TRIP, "best_price": 450.0, "comparable_price": 450.0},
    ]
    deals = filter_deals(trips)
    assert len(deals) == 2


def test_filter_deals_empty_list():
    deals = filter_deals([])
    assert len(deals) == 0


def test_filter_deals_per_person():
    trips = [{**MOCK_TRIP, "best_price": 800.0, "comparable_price": 400.0}]
    deals = filter_deals(trips)
    assert len(deals) == 1
