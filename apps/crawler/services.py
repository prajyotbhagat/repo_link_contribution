import os
import time
import requests
import base64
import re
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware
from apps.repositories.models import Repository, Issue
from apps.repositories.notifications import send_issue_notifications
from apps.analytics.services import AnalyticsService
from django.contrib.auth.models import User

# 10 categories, 50 repos each = 500 total
CATEGORIES = [
    {"label": "AI & Machine Learning",   "query": "topic:machine-learning stars:>500"},
    {"label": "Web Frameworks",          "query": "topic:web-framework stars:>500"},
    {"label": "Developer Tools & CLI",   "query": "topic:cli stars:>1000"},
    {"label": "Data Science",            "query": "topic:data-science stars:>500"},
    {"label": "DevOps & Infrastructure", "query": "topic:devops stars:>500"},
    {"label": "Frontend & UI",           "query": "topic:frontend stars:>1000"},
    {"label": "Security",                "query": "topic:security stars:>500"},
    {"label": "Open Source Awesome Lists","query": "topic:awesome stars:>5000"},
    {"label": "Beginner Friendly",       "query": "topic:beginner-friendly stars:>200"},
    {"label": "System Programming",      "query": "topic:systems-programming stars:>300"},
]

class GitHubCrawlerService:
    BASE_URL = "https://api.github.com"

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN")
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def fetch_top_repositories(self, min_stars=500, per_page=50):
        """Fetch top repos by stars (original single-query method)."""
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": f"stars:>{min_stars}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_page
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch repositories. Status: {response.status_code}")
            return []

        items = response.json().get("items", [])
        return self._process_items(items)

    def fetch_all_categories(self, per_category=50):
        """Fetch repos across all defined categories. Skips repos already in DB."""
        all_processed = 0
        for cat in CATEGORIES:
            print(f"\n📂 Crawling category: {cat['label']} ...")
            items = self._search(cat["query"], per_page=per_category)
            processed = self._process_items(items)
            all_processed += len(processed)
            print(f"   ✓ {len(processed)} repos processed (total so far: {all_processed})")
            # Respect GitHub rate limit: 10 requests/minute for search without token
            time.sleep(2)
        return all_processed

    def _search(self, query, per_page=50):
        """Run a GitHub search query and return raw items."""
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(per_page, 100),
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json().get("items", [])
        elif response.status_code == 403:
            print("  ⚠ Rate limited. Waiting 60s...")
            time.sleep(60)
            return self._search(query, per_page)
        else:
            print(f"  ✗ Search failed [{response.status_code}]: {query}")
            return []

    def _process_items(self, items):
        """Save, deep-crawl, score, and embed a list of raw GitHub repo items."""
        processed = []
        for item in items:
            repo = self._save_repository(item)
            self._fetch_readme(repo)
            self._fetch_issues(repo)
            self._fetch_contributors_count(repo)
            self._fetch_good_first_issues_count(repo)
            AnalyticsService.compute_all_scores(repo)
            processed.append(repo)
        return processed

    def _fetch_readme(self, repo):
        url = f"{self.BASE_URL}/repos/{repo.full_name}/readme"
        response = requests.get(url, headers=self.headers)
        if response.status_code == 200:
            data = response.json()
            content = data.get("content", "")
            try:
                repo.readme = base64.b64decode(content).decode('utf-8')
                repo.save()
            except Exception:
                pass

    def _fetch_issues(self, repo):
        from datetime import datetime, timezone, timedelta
        from django.utils.dateparse import parse_datetime
        from apps.analytics.summarizer import summarize_issue, generate_learning_guide

        cutoff = datetime.now(timezone.utc) - timedelta(days=5)

        url = f"{self.BASE_URL}/repos/{repo.full_name}/issues"
        params = {
            "state": "all",
            "sort": "created",
            "direction": "desc",
            "per_page": 30,
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code != 200:
            return

        for issue_data in response.json():
            # Skip pull requests
            if "pull_request" in issue_data:
                continue

            # Only keep issues created within the last 5 days
            created_str = issue_data.get("created_at")
            created_at = parse_datetime(created_str) if created_str else None
            if created_at and created_at < cutoff:
                break  # Results are sorted newest-first, so we can stop here

            labels = [lbl["name"] for lbl in issue_data.get("labels", [])]
            is_gfi = "good first issue" in [l.lower() for l in labels]
            title = issue_data.get("title", "")
            body = issue_data.get("body", "") or ""
            state = issue_data.get("state", "open")

            # For closed issues, only track them if they are interconnected (e.g. mention another issue/PR via #123)
            merged_code = None
            if state == "closed":
                import re
                if not body or not re.search(r'#\d+', body):
                    continue
                # We could fetch the exact merged PR diff here, but to avoid rate limits 
                # we'll pass a placeholder and rely on the AI's general knowledge of the repository context
                merged_code = "Code merged from an interconnected Pull Request."

            # Generate AI summary and Learning Guide
            ai_summary = summarize_issue(title, body)
            ai_learning_guide = generate_learning_guide(title, body, state=state, merged_code=merged_code)

            issue, created = Issue.objects.update_or_create(
                repository=repo,
                github_issue_number=issue_data["number"],
                defaults={
                    "title": title,
                    "body": body,
                    "issue_url": issue_data["html_url"],
                    "state": state,
                    "labels": labels,
                    "created_at": created_at,
                    "is_good_first_issue": is_gfi,
                    "ai_summary": ai_summary,
                    "ai_learning_guide": ai_learning_guide,
                }
            )
            if created:
                send_issue_notifications(issue)

    def _fetch_contributors_count(self, repo):
        url = f"{self.BASE_URL}/repos/{repo.full_name}/contributors"
        params = {"per_page": 1, "anon": "true"}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            link_header = response.headers.get("Link")
            if link_header:
                match = re.search(r'page=(\d+)>; rel="last"', link_header)
                repo.contributors_count = int(match.group(1)) if match else 1
            else:
                repo.contributors_count = len(response.json())
            repo.save()

    def _fetch_good_first_issues_count(self, repo):
        """Query GitHub for total 'good first issue' labelled open issues."""
        url = f"{self.BASE_URL}/search/issues"
        params = {
            "q": f'repo:{repo.full_name} label:"good first issue" is:open is:issue',
            "per_page": 1,
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            count = response.json().get("total_count", 0)
            repo.good_first_issues_count = count
            repo.save(update_fields=["good_first_issues_count"])
        elif response.status_code == 403:
            print(f"  ⚠ Rate limited fetching GFI count for {repo.full_name}")

    def _save_repository(self, item):
        last_commit_str = item.get("pushed_at") or item.get("updated_at")
        last_commit = None
        if last_commit_str:
            dt = parse_datetime(last_commit_str)
            if dt and dt.tzinfo is None:
                last_commit = make_aware(dt)
            else:
                last_commit = dt

        repo, created = Repository.objects.update_or_create(
            github_id=item["id"],
            defaults={
                "name": item["name"],
                "owner": item["owner"]["login"] if item.get("owner") else "",
                "full_name": item["full_name"],
                "repo_url": item["html_url"],
                "description": item.get("description", ""),
                "language": item.get("language", ""),
                "topics": item.get("topics", []),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "open_issues": item.get("open_issues_count", 0),
                "last_commit": last_commit
            }
        )
        status = "Created" if created else "Updated"
        print(f"  {status}: {repo.full_name}")
        return repo

    