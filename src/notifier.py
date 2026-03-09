import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

from src.scraper import fetch_all_trips

logger = logging.getLogger(__name__)

load_dotenv()
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

def build_email_content(deals: dict) -> str:
    lines = []
    for deal in deals:
        lines.append(
            f"✈️ {deal['origin']} → {deal['destination']}\n"
            f"   📅 {deal['departure_date']} → {deal['return_date']}\n"
            f"   💰 Best price: {deal['best_price']} {deal['currency']}\n"
            f"   🎯 Your max price: {deal['max_price']} {deal['currency']}\n"
        )
    return "\n".join(lines)

def send_email(deals: list[dict]) -> None:
    if not deals:
        logger.info("No deals to notify.")
        return

    subject = f"🚨 Travel Alert — {len(deals)} deal(s) found!"
    body = build_email_content(deals)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
            logger.info(f"Email sent to {EMAIL_RECEIVER} with {len(deals)} deal(s).")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def filter_deals(results: list[dict]) -> list[dict]:
    deals = []
    for result in results:
        if result["best_price"] <= result["max_price"]:
            logger.info(
                f"Deal found: {result['origin']} -> {result['destination']} "
                f"at {result['best_price']} {result['currency']}"
            )
            deals.append(result)
        else:
            logger.info(
                f"No deal: {result['origin']} -> {result['destination']} "
                f"at {result['best_price']} {result['currency']} "
                f"(max: {result['max_price']})"
            )
    return deals

def main():
    results = fetch_all_trips()
    deals = filter_deals(results)
    send_email(deals)

if __name__ == "__main__":
    main()