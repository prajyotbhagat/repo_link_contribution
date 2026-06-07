import logging
import markdown

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
    
    # Plain text version
    body_text = (
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

    # HTML version
    md = markdown.Markdown(extensions=['fenced_code', 'tables'])
    html_summary = md.convert(issue.ai_summary or '*No AI summary available.*')
    html_guide = md.convert(issue.ai_learning_guide or '*No learning guide generated.*')
    html_body = md.convert(issue.body or '*No issue body available.*')
    
    html_message = f"""
    <html>
      <head>
        <style>
          body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
          h1, h2, h3, h4 {{ color: #111; margin-top: 1.5em; margin-bottom: 0.5em; }}
          .header {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 25px; border-left: 4px solid #6366f1; }}
          .section {{ margin-bottom: 30px; }}
          .section-title {{ font-size: 1.2em; font-weight: bold; border-bottom: 2px solid #eaeaea; padding-bottom: 8px; margin-bottom: 15px; }}
          pre {{ background-color: #f1f5f9; padding: 15px; border-radius: 6px; overflow-x: auto; font-size: 0.9em; border: 1px solid #e2e8f0; }}
          code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; background-color: #f1f5f9; padding: 2px 4px; border-radius: 4px; font-size: 0.9em; }}
          pre code {{ background-color: transparent; padding: 0; }}
          a {{ color: #2563eb; text-decoration: none; }}
          a:hover {{ text-decoration: underline; }}
          .btn {{ display: inline-block; background-color: #000; color: #fff; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px; }}
          .btn:hover {{ background-color: #333; text-decoration: none; }}
        </style>
      </head>
      <body>
        <div class="header">
          <div style="font-size: 1.1em; font-weight: bold; margin-bottom: 5px;">Repository: <a href="https://github.com/{issue.repository.full_name}">{issue.repository.full_name}</a></div>
          <div style="font-size: 1.3em; margin-bottom: 15px;">Issue #{issue.github_issue_number}: {issue.title}</div>
          <a href="{issue.issue_url}" class="btn">View Issue on GitHub</a>
        </div>

        <div class="section">
          <div class="section-title">AI Summary</div>
          {html_summary}
        </div>

        <div class="section">
          <div class="section-title">🎓 Learn with Bugs (AI Learning Guide)</div>
          {html_guide}
        </div>

        <div class="section" style="color: #555;">
          <div class="section-title">Original Issue Body</div>
          {html_body}
        </div>
      </body>
    </html>
    """

    for watch in watchers:
        if IssueNotification.objects.filter(user=watch.user, issue=issue).exists():
            continue

        if not watch.user.email:
            continue

        try:
            send_mail(
                subject=subject,
                message=body_text,
                html_message=html_message,
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

