# CourseLens

Course Insight Agent is a Python multi-agent system for course and instructor
questions. It can run as an interactive CLI or as a FastAPI backend for a web
frontend.

## Environment

Create a `.env` file:

```env
GOOGLE_API_KEY=your_google_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the CLI

```bash
python main.py
```

## Run the API

```bash
uvicorn api:app --reload
```

By default the API is available at:

```text
http://127.0.0.1:8000
```

Useful endpoints:

```text
GET  /health
POST /chat
GET  /agents
GET  /stats
POST /clear
```

The API keeps conversation state in per-browser sessions. The frontend stores
the returned `session_id` in local storage and sends it on later requests.

Optional API environment variables:

```env
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
SESSION_TTL_MINUTES=120
MAX_SESSIONS=50
LOG_LEVEL=INFO
```

Example chat request:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What is CMPUT 174 about?","session_id":null}'
```

## Run the Frontend

The React frontend lives in `frontend/`.

```bash
cd frontend
npm install
npm run dev
```

By default the frontend is available at:

```text
http://127.0.0.1:5173
```

The frontend calls the API at `http://127.0.0.1:8000` unless you override it:

```bash
VITE_API_URL=https://your-api-host.example npm run build
```

Build for deployment:

```bash
cd frontend
npm run build
```

## Deploy

This repo is set up for:

- Frontend: Vercel
- Backend API: Render

### 1. Deploy the Backend on Render

Use the included `render.yaml` blueprint, or create a Render Web Service
manually from this repository.

Backend settings:

```text
Runtime: Python
Build command: pip install -r requirements.txt
Start command: uvicorn api:app --host 0.0.0.0 --port $PORT
Health check path: /health
```

Set these Render environment variables:

```env
GOOGLE_API_KEY=your_google_api_key
FIRECRAWL_API_KEY=your_firecrawl_api_key
FRONTEND_ORIGINS=https://your-vercel-app.vercel.app
LOG_LEVEL=INFO
SESSION_TTL_MINUTES=120
MAX_SESSIONS=50
```

After Render deploys, verify:

```text
https://your-render-service.onrender.com/health
```

It should return:

```json
{"status":"ok"}
```

### 2. Deploy the Frontend on Vercel

Create a new Vercel project from this repository and use these settings:

```text
Framework preset: Vite
Root directory: frontend
Build command: npm run build
Output directory: dist
```

Set this Vercel environment variable:

```env
VITE_API_URL=https://your-render-service.onrender.com
```

Deploy the Vercel app, then copy its production URL back into Render's
`FRONTEND_ORIGINS` variable.

### 3. Production Flow

```text
Browser
  -> Vercel React app
  -> Render FastAPI backend
  -> Gemini + Firecrawl
```

For local development, keep using:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000
```
