import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import IssueNotification, RepositoryWatch


logger = logging.getLogger(__name__)


def send_issue_notifications(issue):
    watchers = RepositoryWatch.objects.select_related('user').filter(
        repository=issue.repository,
        user__is_active=True,
    )

    if not watchers.exists():
        return 0

    sent_count = 0
    subject = f"[RepoRadar] New issue in {issue.repository.full_name}: {issue.title}"
    body = (
        f"Repository: {issue.repository.full_name}\n"
        f"Issue: #{issue.github_issue_number} {issue.title}\n"
        f"URL: {issue.issue_url}\n\n"
        "AI Summary:\n"
        f"{issue.ai_summary or 'No AI summary available.'}\n\n"
        "🎓 Learn with Bugs (AI Learning Guide):\n"
        f"{issue.ai_learning_guide or 'No learning guide generated.'}\n\n"
        "Full Issue:\n"
        f"{issue.body or 'No issue body available.'}\n"
    )

    for watch in watchers:
        if IssueNotification.objects.filter(user=watch.user, issue=issue).exists():
            continue

        if not watch.user.email:
            continue

        try:
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[watch.user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(
                "Failed to send notification to %s for issue=%s: %s",
                watch.user.email,
                issue.id,
                str(e),
            )
            continue

        IssueNotification.objects.create(user=watch.user, issue=issue)
        sent_count += 1

    return sent_count
