import os
from django.http import JsonResponse
from apps.crawler.tasks import run_all_categories_task

def trigger_crawler(request):
    """
    Secure endpoint to trigger the Celery crawler task in production.
    Requires a ?token= matching the CRAWLER_SECRET_TOKEN env var.
    """
    provided_token = request.GET.get('token')
    expected_token = os.environ.get('CRAWLER_SECRET_TOKEN')

    if not expected_token:
        return JsonResponse({'error': 'Server configuration missing: CRAWLER_SECRET_TOKEN is not set.'}, status=500)

    if provided_token == expected_token:
        # Dispatch the background task
        run_all_categories_task.delay(per_category=50)
        return JsonResponse({'status': 'Crawler task dispatched successfully! Check Celery worker logs for progress.'})
    
    return JsonResponse({'error': 'Unauthorized: Invalid token.'}, status=403)
