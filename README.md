# ✈️ Travel Monitor

A smart travel price monitor that tracks flight prices to your desired destinations via **Google Flights** and sends beautifully formatted **email alerts** when prices drop below your budget.

Set it up once, and let GitHub Actions check prices for you every day — no server required.

---

## How It Works

1. You define your trips and budget in a simple `users.yml` file.
2. A scheduled GitHub Action runs daily, scraping Google Flights for the best available prices.
3. If any flight is at or below your maximum price, you receive an email with a detailed deal card showing the price, your budget, and how much you save.

---

## Email Alert Preview

When a deal is found, you'll receive an email like this:

```
🚨 Travel Alert — 2 deal(s) found!

  ✈️ OPO → BCN
  Iberia
  📅 2026-06-01
  🔙 2026-06-15
  Best Price: 285 EUR | Your Max: 500 EUR | You Save: 43%
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/travel-monitor.git
cd travel-monitor
```

### 2. Install dependencies

This project uses [Poetry](https://python-poetry.org/) for dependency management.

```bash
pip install poetry
poetry install --no-root
```

Since the scraper runs in local browser mode, you'll also need Playwright's Chromium:

```bash
poetry run playwright install chromium --with-deps
```

### 3. Configure your environment

Copy the example `.env` file and fill in your email credentials:

```bash
cp .env.example .env
```

```env
EMAIL_SENDER=youremail@gmail.com
EMAIL_PASSWORD=your_app_password_here
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
```

> **Note:** If you're using Gmail, you'll need to generate an [App Password](https://support.google.com/accounts/answer/185833) rather than using your regular password.

### 4. Define your trips

Create a `users.yml` file in the project root:

```yaml
users:
  - name: Alice
    email: alice@example.com
    trips:
      - origin: OPO
        destination: BCN
        departure_date: "2026-06-01"
        return_date: "2026-06-15"
        currency: EUR
        airline: IB
        max_price: 500
        adults: 1

      - origin: LIS
        destination: CDG
        departure_date: "2026-07-10"
        departure_time_from: "09:00"
        departure_time_to: "12:00"
        return_date: "2026-07-20"
        return_time_from: "14:00"
        return_time_to: "20:00"
        currency: EUR
        max_price: 300
        adults: 2
        max_price_per_person: true
```

### 5. Run the monitor

```bash
poetry run python -m src.monitor
```

---

## Trip Configuration Reference

Each trip entry in `users.yml` supports the following fields:

| Field | Required | Default | Description |
|---|---|---|---|
| `origin` | Yes | — | IATA airport code for departure (e.g. `OPO`, `JFK`) |
| `destination` | Yes | — | IATA airport code for arrival |
| `departure_date` | Yes | — | Outbound date (`YYYY-MM-DD`) |
| `return_date` | No | — | Return date; omit for one-way trips |
| `max_price` | Yes | — | Maximum acceptable price (total or per person) |
| `currency` | No | `EUR` | Currency code for price comparison |
| `airline` | No | auto | Preferred airline display name |
| `adults` | No | `1` | Number of adult passengers |
| `children` | No | `0` | Number of child passengers |
| `infants` | No | `0` | Number of infant passengers |
| `travel_class` | No | `ECONOMY` | One of `ECONOMY`, `PREMIUM_ECONOMY`, `BUSINESS`, `FIRST` |
| `max_stops` | No | — | Set to `0` for non-stop flights only |
| `max_duration_hours` | No | — | Maximum flight duration in hours |
| `departure_time_from` | No | — | Earliest acceptable outbound departure time (`HH:MM`, 24h) |
| `departure_time_to` | No | — | Latest acceptable outbound departure time (`HH:MM`, 24h) |
| `return_time_from` | No | — | Earliest acceptable return departure time (`HH:MM`, 24h) |
| `return_time_to` | No | — | Latest acceptable return departure time (`HH:MM`, 24h) |
| `max_price_per_person` | No | `false` | If `true`, compares price per person against `max_price` |

---

## Automated Daily Checks with GitHub Actions

The included workflow (`.github/workflows/monitor.yml`) runs the monitor every day at **9:00 AM UTC**.

### Setup

1. Go to your repository **Settings → Secrets and variables → Actions**.
2. Add the following secrets:

| Secret | Description |
|---|---|
| `EMAIL_SENDER` | Your sender email address |
| `EMAIL_PASSWORD` | Your email app password |
| `USERS_YML` | The full contents of your `users.yml` file |

3. The workflow can also be triggered manually via **Actions → Travel Price Monitor → Run workflow**.

---

## Development

### Running Tests

```bash
poetry run pytest tests/
```

### Linting & Formatting

```bash
poetry run ruff check .
poetry run ruff format --check .
```

### Type Checking

```bash
poetry run mypy src/
```

All of these checks run automatically on every push and pull request via the CI workflow (`.github/workflows/ci.yml`).

---

## Project Structure

```
travel-monitor/
├── src/
│   ├── __init__.py          # Logging configuration
│   ├── monitor.py           # Main entry point
│   ├── scraper.py           # Google Flights scraping logic
│   ├── notifier.py          # Deal filtering and email sending
│   └── templates/
│       ├── email.html       # Email wrapper template
│       └── email_card.html  # Individual deal card template
├── tests/
│   └── test_notifier.py     # Unit tests for deal filtering
├── .github/workflows/
│   ├── ci.yml               # CI pipeline (lint, type check, test)
│   └── monitor.yml          # Scheduled price monitoring
├── pyproject.toml            # Project metadata and dependencies
├── .env.example              # Environment variable template
└── users.yml                 # Trip definitions (not committed)
```

---

## Tech Stack

- **[fast-flights](https://github.com/AWeirdDev/fast-flights)** — Google Flights scraper
- **[Playwright](https://playwright.dev/python/)** — Browser automation for local scraping
- **[PyYAML](https://pyyaml.org/)** — User and trip configuration
- **[python-dotenv](https://github.com/theskumar/python-dotenv)** — Environment variable management
- **GitHub Actions** — Scheduled execution and CI/CD

---

## License

This project is for personal and educational use.