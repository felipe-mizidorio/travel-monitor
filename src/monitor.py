from src.scraper import fetch_all_trips
from src.notifier import filter_deals, send_email

def main():
    results = fetch_all_trips()
    deals = filter_deals(results)
    send_email(deals)
    
if __name__ == "__main__":
    main()