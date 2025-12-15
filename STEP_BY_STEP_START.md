# Step-by-Step: Start DevPlatform

Follow these steps **in order** to get everything running.

## ✅ Step 1: Stop Everything (if running)

If you have any terminals running `npm run dev` or `uvicorn`, press `Ctrl+C` to stop them.

## ✅ Step 2: Start Backend

**Open Terminal 1:**

```bash
cd backend
source .venv/Scripts/activate
uvicorn main:app --reload --port 8000
```

**Wait for:** `Uvicorn running on http://0.0.0.0:8000`

**✅ Test it works:**
- Open browser: http://localhost:8000/health
- Should see: `{"status":"ok",...}`

**Keep this terminal open!**

---

## ✅ Step 3: Start Frontend

**Open Terminal 2 (NEW terminal):**

```bash
cd frontend
npm run dev
```

**Wait for:** `VITE v5.4.21 ready in ... ms`

**✅ Test it works:**
- Open browser: http://localhost:5173
- Should see the DevPlatform UI

**Keep this terminal open!**

---

## ✅ Step 4: Fix Frontend Error (if you see error)

If you see error about `App.js` not found:

1. **Stop frontend** (Ctrl+C in Terminal 2)
2. **Clear cache and restart:**

```bash
cd frontend
rm -rf node_modules/.vite
rm -rf dist
npm run dev
```

---

## ✅ Step 5: Access the Application

**Open in browser:**
- Frontend: http://localhost:5173
- Or network IP: http://172.20.10.2:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## ✅ Step 6: Test Features

1. **Health Check:**
   - Click "Check backend health" button
   - Should show service status

2. **Metrics Dashboard:**
   - Scroll to "4) Metrics Dashboard"
   - Click "Refresh Now"
   - Should show HTTP metrics and charts

3. **Logs:**
   - Scroll to "3) Logs"
   - Click "Fetch Logs" or "Start Streaming"
   - (Will show errors without Kubernetes - that's OK)

---

## 🎯 Quick Commands Summary

**Terminal 1 (Backend):**
```bash
cd backend && source .venv/Scripts/activate && uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend && npm run dev
```

**Test Backend:**
```bash
curl http://localhost:8000/health
```

---

## ❌ Troubleshooting

**Backend won't start?**
- Make sure virtual environment is activated: `source .venv/Scripts/activate`
- Check port 8000 is free
- Install dependencies: `pip install -r requirements.txt`

**Frontend shows old UI?**
- Hard refresh browser: `Ctrl + Shift + R`
- Clear Vite cache: `rm -rf node_modules/.vite`
- Restart: `npm run dev`

**Frontend error about App.js?**
- Stop frontend (Ctrl+C)
- Run: `rm -rf node_modules/.vite dist`
- Restart: `npm run dev`

**Can't connect frontend to backend?**
- Check backend is running: http://localhost:8000/health
- Check browser console (F12) for errors
- Verify CORS is working

---

## ✅ Success Checklist

- [ ] Backend running on port 8000
- [ ] Frontend running on port 5173
- [ ] Can access http://localhost:5173
- [ ] Health check button works
- [ ] Metrics dashboard shows data
- [ ] No errors in browser console (F12)

---

**You're all set!** 🚀

