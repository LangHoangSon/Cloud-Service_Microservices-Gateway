# E-Commerce Microservices + Databricks Analytics

> Cloud Computing course project — microservices backend với API Gateway và Databricks analytics pipeline.

---

## Architecture

```
Client / Postman
      │
      ▼
 API Gateway  :8000   ← single entry point, JWT validation, rate limiting
      │
  ┌───┼───────────────┐
  ▼   ▼               ▼
Auth  Product       Order  ──► Notification
:8001 :8002         :8003       :8004
                      │
                  orders.json
                      │
                      ▼
               Databricks (ETL → ML → Dashboard)
```

## Team

| Person | Ownership |
|--------|-----------|
| Sơn (Tech Lead) | `gateway/`, `docker-compose.yml`, `docs/`, `deployment/` |
| Person 2 | `auth_service/`, `product_service/` |
| Person 3 | `order_service/`, `notification_service/`, `data_engineering/`, `databricks/` |

---

## Quick start

### Prerequisites
- Docker + Docker Compose
- Python 3.11+

### Run everything

```bash
git clone <repo>
cd cloud-ecommerce-analytics
docker compose up --build
```

Services will be available at:
- Gateway: http://localhost:8000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### Run gateway locally (without Docker)

```bash
cd services/gateway
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

---

## API Overview

See [`docs/api_contract.md`](docs/api_contract.md) for full request/response schemas.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/register` | No | Register user |
| POST | `/auth/login` | No | Get JWT token |
| GET | `/products` | No | List products |
| POST | `/orders` | Yes | Create order |
| GET | `/orders/{id}` | Yes | Get order |
| GET | `/health` | No | Gateway + service health |

---

## Project Structure

```
cloud-ecommerce-analytics/
├── services/
│   ├── gateway/                # API Gateway (Person 1)
│   ├── auth_service/           # Auth + JWT (Person 2)
│   ├── product_service/        # Product CRUD (Person 2)
│   ├── order_service/          # Orders + orders.json (Person 3)
│   └── notification_service/   # Email notifications (Person 3)
├── data_engineering/           # Data generator + schemas (Person 3)
├── databricks/                 # Notebooks 01–07 (Person 1 + 3)
├── dashboard/                  # Streamlit app (Person 2)
├── docs/                       # API contract, architecture (Person 1)
├── docker-compose.yml
└── README.md
```

---

## Databricks Pipeline

```
01_data_loading.py       → load parquet/json from DBFS
02_data_cleaning.py      → validate, remove nulls
03_feature_engineering.py→ RFM features, time features
04_analytics.py          → revenue charts, top products
05_ml_training.py        → KMeans + sales regression
06_insight_generation.py → auto-written findings
07_pipeline_runner.py    → run all notebooks in sequence
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET` | `super-secret-key-change-in-prod` | Change before any demo |
| `AUTH_SERVICE_URL` | `http://auth_service:8001` | Set by docker-compose |
| `PRODUCT_SERVICE_URL` | `http://product_service:8002` | Set by docker-compose |
| `ORDER_SERVICE_URL` | `http://order_service:8003` | Set by docker-compose |
| `NOTIFICATION_SERVICE_URL` | `http://notification_service:8004` | Set by docker-compose |
