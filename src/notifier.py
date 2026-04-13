from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import os
from pathlib import Path
import smtplib
from string import Template

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
EMAIL_SENDER: str = os.getenv("EMAIL_SENDER", "")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")

SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))

TEMPLATES_DIR = Path(__file__).parent / "templates"
EMAIL_TEMPLATE = Template((TEMPLATES_DIR / "email.html").read_text())
CARD_TEMPLATE = Template((TEMPLATES_DIR / "email_card.html").read_text())
LEG_TEMPLATE = Template((TEMPLATES_DIR / "email_leg.html").read_text())


def _stops_label(stops: int) -> str:
    if stops == 0:
        return "Nonstop"
    return f"{stops} stop" if stops == 1 else f"{stops} stops"


def _extract_time(time_str: str) -> tuple[str, str]:
    """Splits '10:30 PM on Fri, May 8' into ('10:30 PM', 'Fri, May 8')."""
    if " on " in time_str:
        t, day = time_str.split(" on ", 1)
        return t.strip(), day.strip()
    return time_str.strip(), ""


def _leg_html(label: str, date: str, leg: dict) -> str:
    is_outbound = label == "Outbound"
    dep_time, dep_day = _extract_time(leg["departure_time"])
    arr_time, arr_day = _extract_time(leg["arrival_time"])

    return LEG_TEMPLATE.substitute(
        label=label,
        label_bg="#eff6ff" if is_outbound else "#f0fdfa",
        label_color="#2563eb" if is_outbound else "#0d9488",
        date=date,
        dep_time=dep_time,
        arr_time=arr_time,
        next_day_label="+1" if arr_day and dep_day and arr_day != dep_day else "",
        duration=leg["duration"],
        stops_label=_stops_label(leg["stops"]),
        airline=leg["airline"],
    )


def build_email_body(deals: list[dict]) -> str:
    cards = ""
    for deal in deals:
        savings_pct = int(
            ((deal["max_price"] - deal["best_price"]) / deal["max_price"]) * 100
        )

        flight_details = _leg_html("Outbound", deal["departure_date"], deal["outbound"])
        if deal.get("inbound"):
            flight_details += _leg_html("Return", deal["return_date"], deal["inbound"])

        cards += CARD_TEMPLATE.substitute(
            **{
                **deal,
                "best_price": f"{deal['best_price']:.0f}",
                "max_price": f"{deal['max_price']:.0f}",
                "savings_pct": savings_pct,
                "flight_details": flight_details,
                "return_date": deal["return_date"] or "",
            }
        )

    return EMAIL_TEMPLATE.substitute(
        cards=cards,
        deal_count=len(deals),
        deal_plural="s" if len(deals) > 1 else "",
    )


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
    msg.attach(MIMEText(body, "html"))

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
