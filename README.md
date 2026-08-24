# Property Business AI

An AI-powered decision-support platform for business owners and property managers.
Provides real-time operational tracking, financial analytics, and AI-driven action plans.

---

## Technology Stack

| Layer            | Technology                                  |
|------------------|---------------------------------------------|
| Frontend         | HTML5, CSS3, Vanilla JavaScript, Chart.js   |
| Backend          | Python 3.x, Django (Server-Side Rendering)  |
| Database         | MySQL                                       |
| Analytics / ML   | Pandas, NumPy, Scikit-learn *(Phase 4+)*    |
| Authentication   | Django Built-in Session Authentication      |
| Version Control  | Git / GitHub                                |

---

## Project Phases

| Phase | Focus                                              | Status      |
|-------|----------------------------------------------------|-------------|
| 1     | Project foundation, settings, app skeleton         | In Progress |
| 2     | Custom User model, Business setup, Session auth    | Pending     |
| 3     | Products, Inventory, InventoryTransaction ledger   | Pending     |
| 4     | Purchases, Sales, Expenses (Transactions)          | Pending     |
| 5     | Financial Analytics, Pandas integration, Chart.js  | Pending     |
| 6     | AI Action Plan — Rule-based engine (V1)            | Pending     |
| 7     | CSV / Excel data import service                    | Pending     |
| 8     | ML predictions — Scikit-learn pipeline (V2)        | Pending     |
| 9+    | Land / Property / Maintenance modules              | Future      |

---

## Repository Structure

```
property-business-ai/
├── docs/
│   └── ARCHITECTURE.md          # Full technical architecture specification
├── requirements/
│   ├── base.txt                 # Core dependencies
│   ├── local.txt                # Development dependencies
│   └── production.txt           # Production dependencies
├── src/
│   ├── manage.py
│   ├── config/                  # Django project configuration
│   │   ├── settings/
│   │   │   ├── base.py          # Shared settings
│   │   │   ├── local.py         # Development settings
│   │   │   └── production.py    # Production settings
│   │   ├── urls.py
│   │   ├── wsgi.py
│   │   └── asgi.py
│   └── apps/                    # Modular Django applications
│       ├── accounts/            # User authentication & roles
│       ├── businesses/          # Business profiles & multi-tenancy
│       ├── products/            # Product catalog & categories
│       ├── inventory/           # Stock tracking & audit ledger
│       ├── transactions/        # Purchases, sales & expenses
│       ├── analytics/           # Financial summaries & reporting
│       ├── ai_engine/           # Rule-based engine (V1) & ML (V2)
│       └── data_importer/       # CSV / Excel import service
├── .env.example                 # Environment variable template
├── .gitignore
└── README.md
```

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/your-username/property-business-ai.git
cd property-business-ai
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements/local.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your local MySQL credentials and secret key
```

### 5. Run the development server

```bash
cd src
python manage.py runserver
```

---

## Environment Variables

See `.env.example` for a full list of required environment variables.

Key variables:

| Variable      | Description                          |
|---------------|--------------------------------------|
| `SECRET_KEY`  | Django secret key (never commit this)|
| `DEBUG`       | `True` for development, `False` for production |
| `DB_NAME`     | MySQL database name                  |
| `DB_USER`     | MySQL username                       |
| `DB_PASSWORD` | MySQL password                       |
| `DB_HOST`     | MySQL host (default: `127.0.0.1`)    |
| `DB_PORT`     | MySQL port (default: `3306`)         |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hostnames |

---

## Architecture

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full technical architecture
specification including the database ERD, InventoryTransaction audit ledger design,
the two-tier AI intelligence approach, and extensibility guidelines.

---

## Contributing

This is a private development project. Development guidelines:
- Follow PEP 8 for all Python code.
- Keep each Django app focused on a single domain responsibility.
- Never commit `.env` files or secret keys.
- Write descriptive commit messages.

---

## License

Private — All rights reserved.
