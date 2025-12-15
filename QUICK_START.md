# DevPlatform Quick Start

Get up and running in 5 minutes!

## Prerequisites

- Python 3.12+
- Node.js 20+
- npm or yarn

## Step 1: Backend Setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate


pip install -r requirements.txt
```

## Step 2: Start Backend

```bash
# In backend directory with venv activated
uvicorn main:app --reload --port 8000
```

Backend will be available at: `http://localhost:8000`

## Step 3: Frontend Setup

```bash
cd frontend
npm install
```

## Step 4: Start Frontend

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173`

## Step 5: Test It!

1. Open `http://localhost:5173` in your browser
2. Click "Check backend health" - should show healthy status
3. Try the metrics dashboard - will show HTTP request metrics
4. Try log streaming - will show connection status

## What Works Without Additional Setup

✅ **Health Check** - Full service status  
✅ **HTTP Metrics** - Request rate tracking  
✅ **Frontend UI** - All components render  
✅ **API Endpoints** - All endpoints respond

## What Requires Additional Setup

⚠️ **Logs/Metrics from Kubernetes** - Requires KUBE_CONFIG  
⚠️ **Repository Onboarding** - Requires GitHub App credentials  
⚠️ **Production Approvals** - Requires GitHub App + APPROVAL_TOKEN  
⚠️ **Preview Environments** - Requires Kubernetes cluster

## Optional: Set Environment Variables

Create a `.env` file in the `backend` directory:

```env
# For testing (optional)
APPROVAL_TOKEN=test-token-123

# For full functionality (required for onboarding)
GITHUB_APP_ID=your_app_id
GITHUB_INSTALLATION_ID=your_installation_id
GITHUB_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...

# For Kubernetes features (required for logs/metrics)
KUBE_CONFIG=your_kubeconfig_content
```

Then load them:

```bash
# Windows PowerShell
Get-Content .env | ForEach-Object { $line = $_ -split '='; [Environment]::SetEnvironmentVariable($line[0], $line[1]) }

# Linux/Mac
export $(cat .env | xargs)
```

## Verify Installation

Run the test suite:

```bash
cd backend
pytest test_main.py -v
```

All 7 tests should pass! ✅

## Next Steps

- See `TESTING_GUIDE.md` for detailed testing instructions
- See `IMPLEMENTATION_SUMMARY.md` for feature overview
- See `README.md` for full documentation

## Troubleshooting

**Backend won't start?**

- Check Python version: `python --version` (need 3.12+)
- Check port 8000 is free: `netstat -an | findstr 8000` (Windows) or `lsof -i :8000` (Linux/Mac)

**Frontend won't start?**

- Check Node version: `node --version` (need 20+)
- Try deleting `node_modules` and `package-lock.json`, then `npm install` again

**Can't connect frontend to backend?**

- Verify backend is running on port 8000
- Check browser console for CORS errors
- Verify `VITE_API_BASE` is set correctly (defaults to `http://localhost:8000`)
