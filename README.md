# Network Monitor MVP

A minimal uptime monitoring dashboard. Add URLs to monitor, automatically check them every 60 seconds, and view status/uptime/response-time data.

## Features

- Add and remove monitoring targets (URLs)
- Automatic HTTP health checks every 60 seconds
- Online/offline status indicators
- Response time measurement and tracking
- 24-hour uptime percentage calculation
- Response time history (Recharts)
- Error/timeout display
- Persistent SQLite database

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, APScheduler
- **Frontend**: React, TypeScript, Recharts
- **Database**: SQLite

## Quick Start

### Backend
```bash
cd backend
pip install -r requirements.txt
python main.py
# Runs on http://localhost:8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# Runs on http://localhost:5173
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /health | Health check |
| GET | /api/targets | List all targets |
| POST | /api/targets | Create target |
| DELETE | /api/targets/{id} | Delete target |
| GET | /api/targets/{id}/uptime | Get uptime % |
| GET | /api/targets/{id}/recent-checks | Get check history |
