# 🚀 OpenSourceHub - Hybrid Deployment (Vercel + Render)

## Perfect for Hackathon: Frontend on Vercel, Backend on Render

### Why This Approach?
✅ **Vercel**: Best for static frontend (fast, free, global CDN)
✅ **Render**: Best for Python backends (free tier, reliable)
✅ **Easy CORS**: No cross-origin issues
✅ **Separate scaling**: Frontend and backend scale independently

---

## Step 1: Deploy Frontend to Vercel

```bash
# Install Vercel CLI (if not already installed)
npm install -g vercel

# Login to Vercel
vercel login

# Deploy frontend only
vercel --prod

# Your frontend will be live at: https://your-project.vercel.app
```

---

## Step 2: Deploy Backend to Render

### Option A: Automatic (Recommended)
1. **Connect GitHub**: Push your code to GitHub
2. **Go to Render**: [render.com](https://render.com)
3. **Create Web Service**:
   - Connect your GitHub repo
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables**:
   - `GOOGLE_API_KEY`: `AIzaSyAb9AHy07_7AQhb4on2H5VugOUMM-uRyTk`

### Option B: Manual Upload
```bash
# Create a simple backend deployment
# Copy these files to a new directory:
# - backend/
# - requirements.txt
# - programs.json

# Then deploy that directory to Render
```

---

## Step 3: Connect Frontend to Backend

After backend deployment, update `frontend/app.js`:

```javascript
// Replace the API_BASE line:
const API_BASE = "https://your-render-backend.onrender.com"; // Your Render URL
```

Then redeploy frontend:
```bash
vercel --prod
```

---

## Step 4: Test Your Deployment

1. **Frontend**: `https://your-vercel-app.vercel.app`
2. **Backend API**: `https://your-render-app.onrender.com/programs`
3. **Check if SWOC & SSoC appear in the programs list**
4. **Test AI mentor chat**
5. **Test email subscription**

---

## URLs Structure:

- **Frontend**: `https://opensourcehub.vercel.app`
- **Backend**: `https://opensourcehub-backend.onrender.com`
- **API Calls**: Frontend calls `https://backend-url.onrender.com/api/...`

---

## Free Tiers:

- **Vercel**: 100GB bandwidth/month, unlimited static sites
- **Render**: 750 hours/month free, auto-sleep when inactive

**Perfect for hackathon - reliable, fast, and free!** 🎉

---

## Quick Commands:

```bash
# Frontend deployment
npm install -g vercel
vercel login
vercel --prod

# Backend deployment (on Render dashboard)
# 1. Connect GitHub repo
# 2. Python 3, pip install -r requirements.txt
# 3. uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

**Deploy time: ~5-10 minutes total!**
