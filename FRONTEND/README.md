# Network Traffic Anomaly Detection — Frontend

React + Vite + Tailwind CSS dashboard for SOPHOSMIXX.

## Setup
```bash
npm install
cp .env.example .env   # set VITE_API_BASE_URL if your backend isn't on localhost:8000
npm run dev
```
Open http://localhost:5173 — log in with the username/password you created via
`python -m app.bootstrap_db` in the backend.

## Pages
- `/login` — sign in (JWT)
- `/dashboard` — live summary cards, anomaly trend chart, recent anomalies, top IPs
- `/upload` — drag & drop Sophos CSV/XLSX, shows validation + insert results
- `/logs` — paginated, filterable firewall log table
- `/anomalies` — anomaly list -> click a row for full detail + Gemini analysis
- `/assistant` — AI Network Assistant chat
- `/reports` — AI Report Generator (executive summary / incident report / threat overview)
- `/profile` — current user + logout

## Build
```bash
npm run build   # outputs to dist/
```
