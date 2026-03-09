import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")

SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))


def build_email_body(deals: list[dict]) -> str:
    lines = []
    for deal in deals:
        lines.append(
            f"✈️ {deal['origin']} → {deal['destination']} ({deal['airline']})\n"
            f"   📅 {deal['departure_date']} → {deal['return_date']}\n"
            f"   💰 Best price: {deal['best_price']} {deal['currency']}\n"
            f"   🎯 Your max price: {deal['max_price']} {deal['currency']}\n"
        )
    return "\n".join(lines)


def send_email(deals: list[dict], email: str) -> None:
    if not deals:
        logger.info("No deals to notify.")
        return

    subject = f"🚨 Travel Alert — {len(deals)} deal(s) found!"
    body = build_email_body(deals)

    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, email, msg.as_string())
            logger.info(f"Email sent to {email} with {len(deals)} deal(s).")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


def filter_deals(trips: list[dict]) -> list[dict]:
    deals = []
    for trip in trips:
        if trip["comparable_price"] <= trip["max_price"]:
            logger.info(
                f"Deal found: {trip['origin']} -> {trip['destination']} "
                f"at {trip['best_price']} {trip['currency']}"
            )
            deals.append(trip)
        else:
            logger.info(
                f"No deal: {trip['origin']} -> {trip['destination']} "
                f"at {trip['best_price']} {trip['currency']} "
                f"(max: {trip['max_price']})"
            )
    return deals


def main():
    from src.scraper import fetch_all_trips

    users = fetch_all_trips()
    for user in users:
        deals = filter_deals(user["trips"])
        send_email(deals, user["email"])


if __name__ == "__main__":
    main()
