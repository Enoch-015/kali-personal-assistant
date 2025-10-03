# Kali Personal Assistant API

FastAPI backend for the Kali Personal Assistant application.

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
pnpm dev:api
# or directly:
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

4. Access the API:
- API: http://localhost:8000
- Interactive docs: http://localhost:8000/docs
- Alternative docs: http://localhost:8000/redoc

## Project Structure

```
apps/api/
├── src/
│   ├── main.py          # FastAPI application entry point
│   ├── routers/         # API route handlers
│   ├── models/          # Pydantic models
│   ├── services/        # Business logic
│   └── utils/           # Utility functions
├── requirements.txt     # Python dependencies
└── README.md
```
