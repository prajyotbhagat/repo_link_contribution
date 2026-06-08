# 📡 RepoRadar

![RepoRadar Banner](https://via.placeholder.com/1000x200.png?text=RepoRadar+-+AI+Powered+Open+Source+Discovery)

**RepoRadar** is an intelligent, AI-powered open-source repository analyzer and contributor assistant. Designed to bridge the gap between complex open-source codebases and junior developers, it helps users discover high-quality repositories, analyze code architecture, and understand GitHub issues through AI-generated learning guides.

---

## ✨ Core Features

1. **Intelligent Repository Discovery & Scoring**
   - Automatically crawls GitHub to discover repositories.
   - Evaluates and assigns a **Final AI Score** based on four key metrics:
     - *Activity Score*: Recency of commits and issue interactions.
     - *Popularity Score*: Logarithmic calculation of Stars and Forks.
     - *Maintenance Score*: Ratio of open issues to stars.
     - *Beginner Friendliness*: Analyzes the volume of "Good First Issues".
2. **AI Issue Summaries (Powered by Gemini 1.5 Flash)**
   - Distills long, complex GitHub issue threads into concise, readable 3-sentence summaries.
3. **🎓 "Learn with Bugs" Guides (Powered by Llama-3 70B)**
   - Translates open issues into step-by-step educational tutorials for developers.
   - Explains real-world software engineering concepts necessary to resolve the bug.
4. **Automated Rich HTML Email Notifications**
   - Users can "Watch" repositories to receive beautifully formatted HTML emails containing AI summaries and tutorials whenever a new issue is opened.
5. **Continuous Background Synchronization**
   - Uses **Celery** and **Redis** to fetch new issues and calculate embeddings synchronously without blocking the UI.

---

## 🏗️ Architecture & Tech Stack

RepoRadar uses a modern decoupled architecture:

### Frontend
- **React 19** with **Vite** for blazing fast compilation.
- **React Router** for seamless SPA navigation.
- **React Markdown** for securely rendering AI-generated guides.
- **CSS3 / UI**: Custom glassmorphism UI with responsive flexbox layouts.

### Backend
- **Django 5.0** + **Django REST Framework (DRF)**.
- **PostgreSQL** for relational data storage (SQLite for local dev).
- **JWT Authentication** (djangorestframework-simplejwt) for stateless auth.

### AI & Asynchronous Processing
- **Celery & Redis**: Background job processing and scheduled GitHub crawls.
- **Google Generative AI (Gemini)**: Semantic text embeddings (`gemini-embedding-2`) and issue summaries (`gemini-flash-latest`).
- **Groq API**: High-speed inference for Llama-3 70B educational guides.

### Infrastructure
- **Docker & Docker Compose**: Full containerization for backend services.
- **Caddy**: High-performance reverse proxy with automatic HTTPS.
- **Vercel / AWS Amplify**: Frontend CDN deployment.

---

## 📂 Project Structure

```text
RepoRadar/
├── apps/
│   ├── analytics/        # AI Scoring logic, Summarizer (Gemini/Groq), NLP
│   ├── authentication/   # JWT Auth endpoints, User models
│   └── repositories/     # Models (Repo, Issue), Celery Tasks, Notifications
├── config/               # Django settings (base, dev, prod), WSGI, ASGI
├── frontend/             # React SPA Application
│   ├── src/
│   │   ├── api/          # Axios interceptors and API calls
│   │   ├── components/   # Reusable UI components (AuthPanel, ChatDrawer)
│   │   ├── contexts/     # React Contexts (AuthContext)
│   │   └── pages/        # Route components (Dashboard, RepoDetail)
│   └── package.json
├── docker-compose.yml    # Multi-container orchestration
├── Dockerfile            # Backend container definition
└── requirements.txt      # Python dependencies
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` in the root directory. 

| Variable | Description | Required |
|----------|-------------|----------|
| `DJANGO_SECRET_KEY` | Secret key for Django cryptographic signing | Yes |
| `GITHUB_TOKEN` | Personal Access Token to bypass rate limits during crawls | Yes |
| `GROQ_API_KEY` | API Key for generating "Learn with Bugs" guides | Yes |
| `GEMINI_API_KEY` | API Key for Summaries and Embeddings | Yes |
| `DATABASE_URL` | PostgreSQL connection string (Production) | No (Defaults to SQLite) |
| `REDIS_URL` | Redis broker URL | Yes (for Celery) |
| `EMAIL_HOST_USER` | SMTP Username (e.g. Resend) | Yes (for Notifications)|
| `EMAIL_HOST_PASSWORD` | SMTP Password / API Key | Yes |

---

## 🚀 Local Development Setup

### 1. Start the Backend Services (Docker)
Ensure Docker daemon is running, then execute:
```bash
docker compose up --build
```
This single command spins up:
- `web`: The Django API on `http://localhost:8000`
- `redis`: In-memory data store on port `6379`
- `worker`: Celery worker to process AI API calls and GitHub API calls.
- `beat`: Celery scheduler running `crawler.run_all_categories` at 13:15 UTC daily.

### 2. Run Database Migrations
In a new terminal window:
```bash
docker compose exec web python manage.py migrate
```

### 3. Start the Frontend
Navigate into the `frontend` directory:
```bash
cd frontend
npm install
npm run dev
```
Access the application at: **`http://localhost:5173`**

---

## 📡 Key API Endpoints

### Authentication
- `POST /api/auth/register/` - Register a new user
- `POST /api/auth/login/` - Authenticate and receive JWT Pair
- `GET /api/auth/me/` - Retrieve current session data

### Repositories
- `GET /api/repos/` - Search and filter repositories (supports pagination & text search)
- `GET /api/repos/{id}/` - Retrieve deep analytics and recent issues for a repository
- `POST /api/repos/{id}/star/` - Toggle email watch notifications

### Background Tasks (Admin/Trigger)
- *Note: Repositories are crawled daily via Celery Beat, but you can manually trigger a crawl:*
```bash
docker compose exec web python trigger_crawler.py
```

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.