# 🏹 Amentum Sports — Javelin AI Analysis Module

> AI-powered javelin throw biomechanical analysis. Upload a video → get pose analysis, joint angles, scores, coaching recommendations, and a PDF report.

---

## 🏗 Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  React Frontend (Vite)            Deployed on: Vercel         │
│  ├─ Upload page (drag-and-drop, tier selection, Razorpay)     │
│  ├─ Report view (scores, radar chart, video overlay, angles)  │
│  └─ Dashboard (history, progress chart, PDF downloads)       │
└─────────────────────────┬────────────────────────────────────┘
                           │ HTTPS REST
┌─────────────────────────▼────────────────────────────────────┐
│  FastAPI Backend (Python 3.11)    Deployed on: Render / AWS   │
│  ├─ POST /api/upload/             → receive MP4/MOV           │
│  ├─ GET  /api/analyze/{id}        → poll status               │
│  ├─ GET  /api/report/{id}         → full JSON report          │
│  ├─ GET  /api/report/{id}/pdf     → PDF download              │
│  └─ POST /api/payment/*           → Razorpay integration      │
│                                                               │
│  Background Pipeline (asyncio + thread pool):                 │
│  Video → MediaPipe Pose → Joint angles → Scorer →            │
│  Claude AI narrative → PDF → Firebase Storage → Firestore    │
└──────────────────────────────────────────────────────────────┘
```

---

## 📦 Project Structure

```
javelin-ai/
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── routes/
│   │   ├── upload.py              # Video upload + pipeline trigger
│   │   ├── analyze.py             # Status polling
│   │   ├── report.py              # Report fetch + PDF download
│   │   ├── payment.py             # Razorpay order/verify/webhook
│   │   └── auth.py                # Firebase token auth
│   ├── services/
│   │   ├── pose_analyzer.py       # MediaPipe pipeline + overlay
│   │   ├── scorer.py              # Biomechanical scoring engine
│   │   ├── report_generator.py    # Claude AI narrative
│   │   └── pdf_export.py          # ReportLab PDF generation
│   └── utils/
│       ├── firebase.py            # Firestore + Storage helpers
│       └── auth.py                # JWT/Firebase token middleware
├── frontend/
│   ├── index.html                 # Razorpay SDK included here
│   ├── vite.config.js
│   ├── package.json
│   └── src/
│       ├── main.jsx
│       ├── App.jsx                # Router + auth guard
│       ├── pages/
│       │   ├── Landing.jsx        # Marketing homepage
│       │   ├── Login.jsx          # Google Auth
│       │   ├── Upload.jsx         # Upload + payment flow
│       │   ├── ReportView.jsx     # Full analysis report UI
│       │   └── Dashboard.jsx      # History + progress chart
│       ├── components/
│       │   └── Layout.jsx         # Navbar + outlet
│       └── utils/
│           ├── firebase.js        # Firebase client SDK
│           └── api.js             # Axios with auth interceptor
└── .env.example
```

---

## 🚀 Local Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Firebase project (Firestore + Storage + Authentication enabled)
- Razorpay account
- Anthropic API key (optional — falls back to templated narrative)

### 1. Clone & configure

```bash
git clone https://github.com/your-org/javelin-ai.git
cd javelin-ai
cp .env.example backend/.env
cp .env.example frontend/.env    # edit VITE_* variables
```

### 2. Firebase setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Create a project → enable **Firestore**, **Storage**, **Authentication** (Google provider)
3. Download service account JSON → save as `backend/firebase-credentials.json`
4. Copy Web SDK config to `frontend/.env` (VITE_FIREBASE_*)

### 3. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev                        # Vite dev server on :5173
```

Open http://localhost:5173

---

## 🐳 Docker (Backend)

```bash
cd backend
docker build -t amentum-backend .
docker run -p 8000:8000 \
  -v $(pwd)/firebase-credentials.json:/app/firebase-credentials.json \
  --env-file .env \
  amentum-backend
```

---

## ☁️ Production Deployment

### Frontend → Vercel

```bash
cd frontend
npm run build
# Push to GitHub → import in Vercel → set VITE_* env vars
```

### Backend → Render

1. Create a new **Web Service** on [Render](https://render.com)
2. Connect your GitHub repo, set Root Directory to `backend`
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables from `.env.example`
6. Upload `firebase-credentials.json` as a Secret File

---

## 🧠 AI Pipeline Detail

| Step | Library | Description |
|------|---------|-------------|
| Frame extraction | OpenCV | Adaptive stride at 10 FPS |
| Pose detection | MediaPipe Pose (complexity=2) | 33-landmark model |
| Angle computation | NumPy | 3-point angle formula for 8 joint pairs |
| Phase detection | Heuristic + angle thresholds | approach/crossover/power/release/follow-through |
| Release frame | Peak wrist height in release phase | |
| Scoring | Rule-based against IAAF biomechanical norms | 5 sections × weighted contribution |
| AI narrative | Claude claude-sonnet-4-20250514 | 200-word coaching summary |
| PDF | ReportLab | Cover page + score table + angles + narrative |
| Overlay video | OpenCV + MediaPipe drawing utils | Skeleton + angle labels written to MP4 |

---

## 📐 Scoring Model

| Section | Weight | Key Metrics |
|---------|--------|-------------|
| Approach | 15 pts | Trunk lean, hip drive |
| Crossover | 20 pts | Knee flexion, hip-shoulder separation building |
| Power Position | 20 pts | Shoulder draw-back angle, elbow extension |
| Release | 30 pts | Release angle (ideal 30–36°), elbow, block leg |
| Follow-Through | 15 pts | Balance, recovery leg |

---

## 💳 Payment Flow

```
1. User selects tier (₹99 AI / ₹1,999 Coach)
2. POST /api/payment/create-order  →  Razorpay order created
3. Razorpay modal opens in browser
4. User pays → Razorpay callback fires
5. POST /api/payment/verify  →  HMAC-SHA256 signature validated
6. Firestore analysis doc updated: { paid: true, tier }
7. Background pipeline respects tier when building report
```

---

## 🔒 Security Notes

- All API routes require Firebase ID token (`Authorization: Bearer <token>`)
- Videos are ownership-checked before serving
- Razorpay HMAC verification prevents payment spoofing
- Firebase Storage rules should restrict reads to authenticated users
- Never commit `firebase-credentials.json` or `.env` files

---

## 📋 Firestore Collections

| Collection | Doc ID | Purpose |
|-----------|--------|---------|
| `analyses` | `video_id` | Upload metadata + processing status |
| `reports`  | `video_id` | Full scored report + AI narrative |

---

## 🎯 Amentum Sports

> Structured. Affordable. Elite.  
> [www.amentums.com](https://www.amentums.com)
