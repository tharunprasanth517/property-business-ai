# Property Business AI — Architecture Reference

## 1. System Overview

Property Business AI is a server-side rendered (SSR) Django web application providing
operational tracking, financial analytics, and AI-driven action plans for business owners.

All HTML pages are rendered by Django templates. JavaScript is used only for
progressive enhancement (form interactions, Chart.js visualisations, AJAX requests
to Django views where needed). There is no SPA or frontend framework.

---

## 2. High-Level Architecture

```
 [ Browser ]
     |
     |  HTTP Request (form submit / anchor navigation / fetch)
     v
 [ Django URL Router ]  (src/config/urls.py + per-app urls.py)
     |
     v
 [ Django View ]  (class-based or function-based)
     |
     |  ORM Query
     v
 [ MySQL Database ]  (via mysqlclient driver)
     |
     |  QuerySet / model objects
     v
 [ Business Logic / Service Layer ]  (plain Python modules inside each app)
     |
     |  Processed context dict
     v
 [ Django Template ]  (Jinja-style DTL, rendered server-side)
     |
     v
 [ HTML Response ]  --> Browser renders page
```

For analytics and AI modules (Phase 4+), the flow extends:

```
 [ Django View ]
     |
     |  ORM QuerySet → pd.DataFrame()
     v
 [ Analytics / AI Service ]  (Pandas · NumPy · Rule Engine · Scikit-learn)
     |
     v
 [ Structured JSON context / serialised results ]
     |
     v
 [ Django Template + Chart.js ]  --> Browser
```

---

## 3. Modular Django Applications

Each Django app owns a single domain. Apps communicate only through model imports
and clearly defined service interfaces — never by reaching into another app's
internal implementation.

| App              | Domain Responsibility                                                  |
|------------------|------------------------------------------------------------------------|
| `accounts`       | Custom User model, session authentication, role management             |
| `businesses`     | Business profiles, multi-tenant scoping (every record is business-scoped) |
| `products`       | User-defined product catalogue, categories, SKUs, pricing              |
| `inventory`      | Current stock levels, warehouse locations, `InventoryTransaction` ledger |
| `transactions`   | Purchase orders, sales invoices, operational expenses                  |
| `analytics`      | Financial aggregations, P&L computation, Pandas integration            |
| `ai_engine`      | V1 rule-based engine; V2 ML prediction pipeline                        |
| `data_importer`  | CSV / Excel file parsing, validation, and bulk database insertion       |

---

## 4. Database Entity Relationship Blueprint

### 4.1 Core Entities

```
[User] ─── 1:N ──→ [BusinessUser] ←── N:1 ─── [Business]
                                                    │
               ┌────────────────┬─────────────────┬─┴────────────────┐
               ↓                ↓                 ↓                  ↓
          [Category]        [Supplier]        [Customer]         [Warehouse]
               │
               ↓ 1:N
          [Product]
               │
        ┌──────┴──────────┐
        ↓                 ↓
  [StockLevel]   [InventoryTransaction]   ← audit ledger (see §4.2)
        
[Business] ──→ [Purchase] ──→ [PurchaseItem] ──→ [Product]
[Business] ──→ [Sale]     ──→ [SaleItem]     ──→ [Product]
[Business] ──→ [ExpenseCategory] ──→ [Expense]
[Business] ──→ [AIActionPlan]
[Business] ──→ [ImportLog]
```

### 4.2 InventoryTransaction Audit Ledger

Every stock movement is recorded as an immutable ledger entry.
No stock level is ever changed without a corresponding `InventoryTransaction` row.

**Transaction Types:**

| Type         | Triggered By                                |
|--------------|---------------------------------------------|
| `PURCHASE`   | Supplier purchase order received            |
| `SALE`       | Customer sale processed                     |
| `RETURN_IN`  | Customer returns goods back                 |
| `RETURN_OUT` | Business returns goods to supplier          |
| `DAMAGE`     | Stock written off due to damage / expiry    |
| `ADJUSTMENT` | Manual stock correction by authorised user  |

**Fields (planned for Phase 3):**

```
InventoryTransaction
  - id
  - business          (FK → Business)
  - product           (FK → Product)
  - transaction_type  (PURCHASE | SALE | RETURN_IN | RETURN_OUT | DAMAGE | ADJUSTMENT)
  - quantity_change   (positive = stock in, negative = stock out)
  - quantity_before   (snapshot of stock level before this transaction)
  - quantity_after    (snapshot of stock level after this transaction)
  - reference_id      (optional FK to Purchase, Sale, etc.)
  - notes             (free text)
  - performed_by      (FK → User)
  - created_at        (auto timestamp)
```

This design guarantees a full audit trail and makes the current stock level
re-computable from ledger history at any point in time.

---

## 5. Authentication Strategy

- **V1**: Django's built-in session authentication (`django.contrib.auth`).
- Login / logout handled via Django's `LoginView` / `LogoutView`.
- Custom `User` model extends `AbstractUser` to allow future field additions
  without breaking migrations.
- JWT will only be introduced if an API-first mobile or third-party integration
  is required in a future phase.

---

## 6. Frontend Rendering Strategy

- **All pages** are rendered server-side via Django Templates (`.html` files in `src/templates/`).
- CSS is authored in `src/static/css/` — plain CSS3 with custom properties (variables).
- JavaScript is authored in `src/static/js/` — vanilla ES6+ modules.
- **Chart.js** is the only charting library. It is loaded via CDN in the base template
  and used for financial dashboard visualisations.
- No React, Vue, Angular, or SPA framework is used.

---

## 7. Two-Tier Intelligence Strategy

### Tier 1 — Rule-Based Engine (V1, available from Day 1)

Does not require historical data. Evaluates current state against configurable thresholds:

- Stock turnover ratio < threshold → "Slow-moving inventory" alert.
- Product stock level < reorder point → "Reorder required" notification.
- Expense ratio > % of revenue → "Operating cost pressure" warning.
- Gross margin < target % → "Margin compression" action item.
- Generates a Business Health Score (0–100) from weighted rule outcomes.

### Tier 2 — Machine Learning Pipeline (V2, available after ≥ 60 days of data)

Activated automatically once sufficient historical data exists:

- Demand forecasting via time-series regression (Scikit-learn).
- Sales trend prediction.
- Seasonal product performance analysis.
- Price optimisation suggestions.

---

## 8. CSV / Excel Import Pipeline

```
User uploads file  →  Django view receives file
    ↓
data_importer app reads file with pd.read_csv() / pd.read_excel()
    ↓
Row-by-row validation against schema rules
    ↓
Valid rows → bulk_create() inside db.transaction.atomic()
Invalid rows → Collected into ImportLog.error_details (JSON)
    ↓
ImportLog record saved with status: SUCCESS | PARTIAL | FAILED
    ↓
User sees import summary on confirmation page
```

Large files are processed in chunks (`chunksize=500`) to prevent memory spikes.

---

## 9. Extensibility Design — Future Modules

The following modules are **NOT** implemented in V1 but are architecturally planned.
They will be added as new Django apps that reference the existing `businesses`,
`products`, and `transactions` apps without modifying them.

| Future Module         | Django App Name        | Anchors To              |
|-----------------------|------------------------|-------------------------|
| Land / Plot Analysis  | `land_analysis`        | `businesses`, `accounts`|
| Property Management   | `property_management`  | `businesses`, `accounts`|
| Maintenance Tracking  | `maintenance`          | `businesses`, `inventory`|
| Tenant / Lease Mgmt   | `tenancy`              | `property_management`   |
| Property ML Valuation | `ai_engine` (extended) | All data apps            |

---

## 10. Settings Strategy

Settings are split into three environment-specific files:

```
config/settings/
    base.py        ← shared: apps, middleware, templates, auth, i18n
    local.py       ← development: DEBUG=True, local MySQL, verbose logging
    production.py  ← production: DEBUG=False, security headers, allowed hosts
```

The active settings module is selected via the `DJANGO_SETTINGS_MODULE`
environment variable defined in `.env`.

---

## 11. Dependency Strategy

Dependencies are added only when the relevant application phase begins.
This keeps the environment minimal and auditable.

| Phase | New Dependencies Added                                  |
|-------|---------------------------------------------------------|
| 1     | Django, python-dotenv, mysqlclient                      |
| 4+    | pandas, numpy                                           |
| 5+    | scikit-learn                                            |
| Prod  | gunicorn                                                |
