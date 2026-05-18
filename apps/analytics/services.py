import math
from datetime import datetime, timezone
from apps.repositories.models import Repository, Issue
from apps.analytics.nlp import analyze_readme_quality

import os
import google.generativeai as genai

class AnalyticsService:
    @staticmethod
    def calculate_popularity_score(repo):
        # Logarithmic scale for popularity (e.g., 100k stars = 100)
        # Using log10: log10(100,000) = 5
        score = (math.log10(repo.stars + 1) * 15) + (math.log10(repo.forks + 1) * 5)
        return min(100.0, score)

    @staticmethod
    def calculate_activity_score(repo):
        if not repo.last_commit:
            return 0.0
        
        now = datetime.now(timezone.utc)
        days_since_commit = (now - repo.last_commit).days
        
        # High score for commits within last 7 days, decays after that
        if days_since_commit <= 7:
            recency_score = 100.0
        else:
            recency_score = max(0.0, 100.0 - (days_since_commit / 3.0))
            
        # Issues activity proxy
        issue_activity = min(100.0, repo.open_issues / 10.0)
        
        return (recency_score * 0.7) + (issue_activity * 0.3)

    @staticmethod
    def calculate_maintenance_score(repo):
        # Proxy for maintenance: how frequently are they committing relative to size
        if repo.stars == 0:
            return 50.0
        
        ratio = repo.open_issues / repo.stars
        # If open issues are extremely high relative to stars, maintenance is lacking
        if ratio > 0.1:
            return max(0.0, 100 - (ratio * 100))
        return 90.0

    @staticmethod
    def calculate_beginner_score(repo):
        total_open = repo.open_issues
        if total_open == 0:
            return 0.0
        
        # We need to query issues model for "good first issue"
        good_first_issues = repo.issues.filter(is_good_first_issue=True).count()
        
        ratio = good_first_issues / total_open
        score = ratio * 1000  # Multiplied because the ratio is usually very small (e.g. 5/500 = 0.01)
        
        return min(100.0, score)

    @staticmethod
    def compute_all_scores(repo):
        repo.popularity_score = AnalyticsService.calculate_popularity_score(repo)
        repo.activity_score = AnalyticsService.calculate_activity_score(repo)
        repo.maintenance_score = AnalyticsService.calculate_maintenance_score(repo)
        repo.doc_score = analyze_readme_quality(repo.readme)
        repo.beginner_score = AnalyticsService.calculate_beginner_score(repo)
        
        repo.final_score = (
            repo.activity_score * 0.30 +
            repo.beginner_score * 0.25 +
            repo.doc_score * 0.20 +
            repo.popularity_score * 0.15 +
            repo.maintenance_score * 0.10
        )
        
        # Generate Vector Embedding using Gemini API
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
                topics_str = " ".join(repo.topics) if repo.topics else ""
                readme_snippet = (repo.readme or "")[:1000]
                text_to_embed = f"{repo.name}. {repo.description}. Topics: {topics_str}. README: {readme_snippet}"
                
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=text_to_embed,
                    task_type="retrieval_document"
                )
                repo.embedding = result['embedding']
        except Exception as e:
            print(f"Error generating embedding for {repo.name}: {e}")

        repo.save()
