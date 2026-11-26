# Deploying VoxLead AI to Vercel

This guide explains how to deploy **VoxLead AI** (React + Vite Frontend and FastAPI + pgvector Backend) on Vercel.

---

## Architecture Considerations for Vercel

Vercel provides a serverless execution environment:
- **Frontend (Vite / React)**: Statically compiled and deployed to Vercel's global Edge CDN.
- **Backend (FastAPI)**: Deployed as Python Serverless Functions (`@vercel/python`) routing `/api/*` and `/health`.
- **Database (PostgreSQL + pgvector)**: Requires a hosted PostgreSQL instance supporting `pgvector` (e.g., [Neon.tech](https://neon.tech), [Supabase](https://supabase.com), or [AWS RDS](https://aws.amazon.com/rds/postgresql/)).
- **Real-Time WebRTC Media (LiveKit)**: WebRTC media audio channels require persistent UDP/TCP streaming sockets handled via [LiveKit Cloud](https://livekit.io) or an external LiveKit media server instance, while room tokens and conversational turn processing are executed serverlessly by FastAPI.

---

## Option 1: Unified Monorepo Deployment (Recommended)

In this approach, a single Vercel project deploys both the frontend and backend together using the root `vercel.json`.

### 1. Project Files in Repository
- `vercel.json` (at root):
  ```json
  {
    "version": 2,
    "builds": [
      {
        "src": "api/index.py",
        "use": "@vercel/python"
      },
      {
        "src": "frontend/package.json",
        "use": "@vercel/static-build",
        "config": {
          "distDir": "dist"
        }
      }
    ],
    "routes": [
      { "src": "/health", "dest": "api/index.py" },
      { "src": "/ready", "dest": "api/index.py" },
      { "src": "/api/(.*)", "dest": "api/index.py" },
      { "handle": "filesystem" },
      { "src": "/(.*)", "dest": "frontend/index.html" }
    ]
  }
  ```
- `api/index.py` (at root): Bridges requests into `backend.app.main:app`.
- `requirements.txt` (at root): Python dependencies installed automatically by Vercel.

### 2. Deployment Steps via Vercel Dashboard
1. Go to [vercel.com/new](https://vercel.com/new) and import `alfeenafsal11/voxlead-ai`.
2. Keep **Root Directory** as `./` (default).
3. Under **Environment Variables**, add the required environment keys (see below).
4. Click **Deploy**.

---

## Option 2: Decoupled Multi-Project Deployment

If you prefer deploying the Frontend and Backend as two isolated Vercel projects:

### Project A: Backend API
1. Import the repository and set **Root Directory** to `./`.
2. Vercel automatically deploys `api/index.py` at `https://<backend-project>.vercel.app`.
3. Set your environment variables in the project settings.

### Project B: Frontend Client
1. Import the repository and set **Root Directory** to `frontend`.
2. **Framework Preset**: `Vite`.
3. Under **Build & Development Settings**:
   - Build Command: `npm run build`
   - Output Directory: `dist`
4. In `frontend/vercel.json`, configure rewrites pointing to your backend URL:
   ```json
   {
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://<backend-project>.vercel.app/api/:path*"
       },
       {
         "source": "/health",
         "destination": "https://<backend-project>.vercel.app/health"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```

---

## Required Environment Variables on Vercel

Configure these in **Project Settings → Environment Variables**:

| Variable | Description | Example / Recommended |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL connection string with pgvector enabled | `postgresql://user:pass@ep-cool-db.us-east-2.aws.neon.tech/voxlead?sslmode=require` |
| `ENVIRONMENT` | Deployment environment | `production` |
| `MOCK_MODE` | Set to `false` for real external APIs or `true` for mock testing | `false` |
| `SECRET_KEY` | JWT signing secret (min 32 characters) | `voxlead-super-secret-production-key-32-chars` |
| `DEFAULT_TENANT_ID` | Default tenant identifier | `tenant-voxlead-demo` |
| `OPENAI_API_KEY` | OpenAI API key for LLM & embeddings | `sk-...` |
| `OPENAI_MODEL` | Conversational LLM model | `gpt-4o` |
| `OPENAI_EMBEDDING_MODEL`| Embedding model | `text-embedding-3-small` |
| `DEEPGRAM_API_KEY` | Streaming STT key | `...` |
| `ELEVENLABS_API_KEY` | Streaming TTS key | `...` |
| `LIVEKIT_URL` | LiveKit server / cloud WebSocket URL | `wss://<project>.livekit.cloud` |
| `LIVEKIT_API_KEY` | LiveKit API Key | `API...` |
| `LIVEKIT_API_SECRET` | LiveKit API Secret | `...` |
| `GOOGLE_CALENDAR_CLIENT_ID` | Google OAuth Client ID | `...` |
| `GOOGLE_CALENDAR_CLIENT_SECRET` | Google OAuth Secret | `...` |
| `GOOGLE_CALENDAR_REFRESH_TOKEN` | Google OAuth Refresh Token | `...` |
| `HUBSPOT_ACCESS_TOKEN` | HubSpot Private App Token | `pat-...` |

---

## Setting up Hosted PostgreSQL with pgvector (e.g. Neon or Supabase)

1. **Neon ([neon.tech](https://neon.tech))**:
   - Create a free serverless PostgreSQL project.
   - Run in SQL Editor:
     ```sql
     CREATE EXTENSION IF NOT EXISTS vector;
     ```
   - Copy connection string into `DATABASE_URL`.

2. **Supabase ([supabase.com](https://supabase.com))**:
   - Create a project and navigate to **Database → Extensions**.
   - Enable `vector`.
   - Copy the connection string (Port 5432 or 6543 pooler) into `DATABASE_URL`.
