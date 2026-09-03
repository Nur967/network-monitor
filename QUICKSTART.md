# Quick Start Guide

## Running the Application

### Terminal 1: Start Backend
```bash
cd backend
pip install -r requirements.txt  # if not already done
python main.py
```

Backend runs on: **http://localhost:8000**
- Health check: `http://localhost:8000/health`

### Terminal 2: Start Frontend
```bash
cd frontend
npm install  # if not already done
npm run dev
```

Frontend runs on: **http://localhost:5173**

## Verification

1. Start the backend (Terminal 1)
2. Start the frontend (Terminal 2)
3. Open **http://localhost:5173** in your browser
4. You should see:
   - ✓ Title: "Network Monitor"
   - ✓ Status: "Backend connected"

## If Backend Connection Fails

- [ ] Check backend is running (`python main.py` output visible)
- [ ] Check port 8000 is not blocked
- [ ] Check no firewall is blocking localhost:8000
- [ ] Restart both services

## Build for Production

Frontend production build:
```bash
cd frontend
npm run build
# Output: dist/ directory with optimized files
```

## Project Structure

```
.
├── backend/
│   ├── main.py              # FastAPI app
│   └── requirements.txt      # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # Main React component
│   │   ├── main.tsx         # React entry point
│   │   └── index.css        # Styling
│   ├── index.html           # HTML template
│   ├── package.json         # NPM config
│   ├── vite.config.ts       # Vite config
│   └── node_modules/        # Dependencies
├── README.md                 # Project documentation
└── .gitignore               # Git ignore rules
```
