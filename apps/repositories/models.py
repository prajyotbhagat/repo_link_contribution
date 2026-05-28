from django.conf import settings
from django.db import models
import uuid

class Repository(models.Model):
    github_id = models.BigIntegerField(unique=True)
    name = models.CharField(max_length=255)
    owner = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    repo_url = models.URLField()
    description = models.TextField(blank=True, null=True)
    readme = models.TextField(blank=True, null=True)
    language = models.CharField(max_length=100, blank=True, null=True)
    topics = models.JSONField(default=list, blank=True)
    stars = models.IntegerField(default=0)
    forks = models.IntegerField(default=0)
    open_issues = models.IntegerField(default=0)
    contributors_count = models.IntegerField(default=0)
    good_first_issues_count = models.IntegerField(default=0)
    activity_score = models.FloatField(default=0)
    beginner_score = models.FloatField(default=0)
    doc_score = models.FloatField(default=0)
    popularity_score = models.FloatField(default=0)
    maintenance_score = models.FloatField(default=0)
    final_score = models.FloatField(default=0)
    last_commit = models.DateTimeField(null=True, blank=True)
    
    # AI Embeddings
    embedding = models.JSONField(null=True, blank=True)

    def __str__(self):
        return self.full_name

class Issue(models.Model):
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='issues'
    )
    github_issue_number = models.IntegerField(default=0)
    title = models.CharField(max_length=500)
    body = models.TextField(blank=True, null=True)
    issue_url = models.URLField()
    state = models.CharField(max_length=20, default='open')
    labels = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(null=True, blank=True)
    difficulty_score = models.FloatField(default=0)
    is_good_first_issue = models.BooleanField(default=False)
    ai_summary = models.TextField(blank=True, null=True)
    ai_learning_guide = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('repository', 'github_issue_number')

    def __str__(self):
        return f"{self.repository.name} - {self.title}"


class RepositoryWatch(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='repository_watches',
    )
    repository = models.ForeignKey(
        Repository,
        on_delete=models.CASCADE,
        related_name='watches',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'repository')

    def __str__(self):
        return f"{self.user} watches {self.repository.full_name}"


class IssueNotification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='issue_notifications',
    )
    issue = models.ForeignKey(
        Issue,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'issue')

    def __str__(self):
        return f"Notification sent to {self.user} for issue {self.issue_id}"


class BeginnerChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_sessions')
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Chat for {self.issue.title} by {self.user}"


class ChatMessage(models.Model):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    )
    session = models.ForeignKey(BeginnerChatSession, on_delete=models.CASCADE, related_name='messages')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role} message in {self.session.id}"
