# Network Traffic Anomaly Detection — Backend

FastAPI + PostgreSQL + Isolation Forest (+LOF) + Gemini AI explanation layer.

## Architecture
```
Sophos Firewall Logs (CSV/XLSX upload)
      -> FastAPI (validate, normalize columns)
      -> PostgreSQL (network.firewall_logs)
      -> Feature Engineering + Preprocessing (app/ml)
      -> Isolation Forest + LOF (production_network_anomaly_pipeline.joblib)
      -> PostgreSQL (network.anomaly_results)
      -> Gemini API (only for confirmed anomalies)
      -> PostgreSQL (network.llm_analysis)
      -> FastAPI JSON API -> React + Tailwind dashboard
```

## 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in:
- `DATABASE_URL` — your PostgreSQL connection string
- `GEMINI_API_KEY` — get a free-tier key at https://aistudio.google.com/apikey
- `JWT_SECRET_KEY` — already pre-filled with a random value; change it for real deployments

## 2. Create the database

```sql
CREATE DATABASE network_anomaly_db;
```
(The `network` schema and all tables are created by the bootstrap script below — you don't need to create them by hand.)

## 3. Create tables + your login

```bash
python -m app.bootstrap_db --username admin --password 'ChangeMe123!'
```
Re-running this later without `--password` just re-creates any missing tables; it won't touch existing users.

## 4. Run

```bash
uvicorn app.main:app --reload --port 8000
```
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## 5. ML pipeline

`models/production_network_anomaly_pipeline.joblib` is your already-trained pipeline
(IsolationForest + LocalOutlierFactor + RobustScaler + selected features + calibrated
thresholds) from `ANOMALY_DETECTION/Network_Traffic.ipynb`. It is loaded once at startup
— it is never retrained by the API. `app/ml/feature_engineering.py` and
`app/ml/preprocessing.py` reproduce your notebook's Stage 2/4/5 transformations exactly
so a fresh uploaded row goes through the identical pipeline the model was trained on.

**Important:** keep `scikit-learn==1.9.0` (already pinned in requirements.txt) — this
matches the version the model was trained with. A mismatched version still runs, but
scikit-learn's own `InconsistentVersionWarning` means results can silently differ.

## 6. Uploading logs

`POST /api/logs/upload` accepts `.csv`, `.xlsx`, `.xls` with the 19 Sophos columns
(Time, Log comp, Log subtype, Username, Firewall rule, Firewall rule name, NAT rule,
NAT rule name, In interface, Out interface, Src IP, Dst IP, Src port, Dst port,
Protocol, Rule type, Live PCAP, Message, Log occurrence). Valid rows are inserted,
detection runs automatically, and Gemini is called automatically for any detected
anomaly (skipped silently if `GEMINI_API_KEY` isn't set — you can trigger it later
per-anomaly from `POST /api/llm/analyze/{anomaly_id}`).

A ready-to-use sample file matching this schema is in `tests/sample_data_raw.csv`.

## 7. AI Network Assistant & AI Report Generator

- `POST /api/assistant/chat` — conversational Q&A. The backend queries PostgreSQL for
  a live snapshot (summary + recent anomalies + anomaly history for any IP mentioned)
  and hands that as context to Gemini. Gemini never queries the database directly.
- `POST /api/reports/generate` — `{"period": "7d", "report_type": "executive_summary"}`.
  Periods: `today`, `7d`, `30d`, `all`. Types: `executive_summary`, `incident_report`,
  `threat_overview`. Same pattern: backend gathers real stats, Gemini writes the prose.

## 8. Tests

```bash
pytest
```
