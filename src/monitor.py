from src.scraper import fetch_all_trips
from src.notifier import filter_deals, send_email


def main():
    users = fetch_all_trips()
    for user in users:
        deals = filter_deals(user["trips"])
        send_email(deals, user["email"])


if __name__ == "__main__":
    main()
