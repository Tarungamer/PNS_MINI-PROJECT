# Adaptive Personalized Nutrition Recommendation System

This repository contains a minimal prototype of the "Adaptive Personalized Nutrition Recommendation System".

Structure:

- `backend/` - Flask API, scoring engine and utility functions

Quickstart (Windows / cmd.exe):

1. Create and activate a Python virtual environment (recommended):

```cmd
python -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```cmd
pip install -r backend/requirements.txt
```

3. Run the API:

```cmd
set FLASK_APP=backend.app
set FLASK_ENV=development
python -m flask run --port 5000
```

4. Example API requests (use curl or Postman):

Register user:

```cmd
curl -X POST http://127.0.0.1:5000/register -H "Content-Type: application/json" -d @examples/register_payload.json
```

Get recommendation:

```cmd
curl -X POST http://127.0.0.1:5000/recommend -H "Content-Type: application/json" -d "{\"user_id\": \"user_1\"}"
```

Weekly update:

```cmd
curl -X POST http://127.0.0.1:5000/weekly-update -H "Content-Type: application/json" -d @examples/weekly_feedback.json
```

Notes:

- This is a prototype scaffold focusing on the backend and algorithms. A React frontend is out-lined in `frontend/README.md`.
- The ML engine uses a heuristic scorer by default and will optionally use `scikit-learn` if available.
"# PNS_MINI-PROJECT" 
