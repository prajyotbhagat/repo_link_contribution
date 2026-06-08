# RepoRadar

RepoRadar is an AI-powered repository analyzer and open-source contribution assistant. It helps developers discover quality open-source repositories and provides AI-generated guides for resolving GitHub issues.

## 🚀 Features

- **Repository Analytics & Scoring**: Automatically crawls GitHub to score repositories based on activity, popularity, maintenance, and beginner-friendliness.
- **AI Issue Summaries**: Uses the **Google Gemini API** to generate concise, readable summaries of complex GitHub issues.
- **🎓 Learn with Bugs**: Uses the **Groq API (Llama-3 70B)** to generate step-by-step beginner guides and educational tutorials on how to solve open issues.
- **Automated Email Notifications**: Users can "Watch" repositories to receive beautifully formatted, rich-HTML email notifications containing AI summaries and learning guides whenever a new issue is opened.
- **Automated Background Crawling**: Uses Celery and Redis to continuously crawl GitHub for new repositories and issues without blocking the main web server.

## 🏗️ Architecture Stack

- **Frontend**: React (Vite) + React Router + React Markdown
- **Backend**: Django REST Framework
- **Database**: PostgreSQL (Production) / SQLite (Local)
- **Task Queue**: Celery + Redis
- **AI Integration**: Google Generative AI (Gemini), Groq (Llama-3)
- **Deployment**: Docker Compose, Caddy (Reverse Proxy), Gunicorn

## 📋 Prerequisites

To run RepoRadar locally, you will need:
- Docker and Docker Compose
- Python 3.10+
- Node.js 18+ (for frontend development)
- A GitHub Personal Access Token
- API Keys for Google Gemini and Groq
- An SMTP provider (like Resend) for email notifications

## 🛠️ Local Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/RepoRadar.git
cd RepoRadar
```

### 2. Environment Variables
Copy the `.env.example` file to `.env`:
```bash
cp .env.example .env
```
Make sure to fill in your `GITHUB_TOKEN`, `GEMINI_API_KEY`, `GROQ_API_KEY`, and SMTP details if you want to test email notifications.

### 3. Run with Docker Compose
The easiest way to run the entire stack (Django, Celery, Redis) locally is using Docker Compose:
```bash
docker compose up --build
```
This will start:
- `web`: The Django API running on `http://localhost:8000`
- `worker`: Celery worker for background jobs
- `beat`: Celery beat for scheduled tasks (like the daily crawler)
- `redis`: Redis broker for Celery

### 4. Run the Frontend Locally
Open a new terminal window, navigate to the `frontend` directory, and start the Vite development server:
```bash
cd frontend
npm install
npm run dev
```
The frontend will be available at `http://localhost:5173`.

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.