import math
from django.http import HttpResponse
from django.contrib.auth import authenticate, get_user_model, login, logout
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Repository, RepositoryWatch
from .serializers import RepositorySerializer


User = get_user_model()

import os
import google.generativeai as genai


def cosine_similarity(v1, v2):
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_v1 = math.sqrt(sum(a * a for a in v1))
    norm_v2 = math.sqrt(sum(b * b for b in v2))
    if norm_v1 == 0 or norm_v2 == 0:
        return 0.0
    return dot_product / (norm_v1 * norm_v2)


def serialize_user(user):
    return {
        'id': user.id,
        'email': user.email,
        'username': user.get_username(),
    }


class AuthStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'authenticated': False, 'user': None})
        return Response({'authenticated': True, 'user': serialize_user(request.user)})


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'An account with that email already exists.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.create_user(username=email, email=email, password=password)
        login(request, user)
        return Response({'authenticated': True, 'user': serialize_user(user)}, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        authenticated_user = authenticate(request, username=user.username, password=password)
        if not authenticated_user:
            return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        login(request, authenticated_user)
        return Response({'authenticated': True, 'user': serialize_user(authenticated_user)})


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'authenticated': False, 'user': None})


class RepositoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Repository.objects.all()
    serializer_class = RepositorySerializer

    @action(detail=False, methods=['get'])
    def top(self, request):
        limit = min(int(request.query_params.get('limit', 500)), 500)
        top_repos = Repository.objects.order_by('-final_score')[:limit]
        serializer = self.get_serializer(top_repos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def recent_issues(self, request, pk=None):
        """GET /api/repos/{id}/recent_issues/ — open issues from the last 5 days."""
        from datetime import datetime, timezone, timedelta
        from .serializers import IssueSerializer

        repo = self.get_object()
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        issues = repo.issues.filter(
            created_at__gte=cutoff, state='open'
        ).order_by('-created_at')
        serializer = IssueSerializer(issues, many=True)
        return Response({
            'repository': repo.full_name,
            'count': issues.count(),
            'issues': serializer.data,
        })

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        query = request.query_params.get('query', '').strip()
        language = request.query_params.get('language')
        limit = min(int(request.query_params.get('limit', 50)), 500)

        repos = Repository.objects.all()

        if language:
            repos = repos.filter(language__iexact=language)

        api_key = os.environ.get("GEMINI_API_KEY")

        # Robust check to see if database has vector embeddings populated
        has_embeddings = False
        if query and api_key:
            has_embeddings = repos.exclude(embedding__isnull=True).exclude(embedding=[]).exists()

        if query and api_key and has_embeddings:
            genai.configure(api_key=api_key)
            try:
                result = genai.embed_content(
                    model="models/text-embedding-004",
                    content=query,
                    task_type="retrieval_query"
                )
                query_embedding = result['embedding']

                repos_list = list(repos)
                scored_repos = []
                for repo in repos_list:
                    if repo.embedding:
                        sim = cosine_similarity(query_embedding, repo.embedding)
                        scored_repos.append((sim, repo))
                    else:
                        scored_repos.append((-1.0, repo))

                scored_repos.sort(key=lambda x: x[0], reverse=True)
                repos_res = [repo for sim, repo in scored_repos][:limit]
                
                serializer = self.get_serializer(repos_res, many=True)
                return Response(serializer.data)
            except Exception as e:
                print(f"Error generating query embedding: {e}")

        # --- FALLBACK TEXT SEARCH ---
        # If semantic search is unavailable, unsupported, or fails, run standard SQL keyword matching
        if query:
            from django.db.models import Q
            words = query.split()
            q_objects = Q()
            for word in words:
                q_objects &= (
                    Q(name__icontains=word) |
                    Q(description__icontains=word) |
                    Q(language__icontains=word) |
                    Q(owner__icontains=word)
                )
            repos = repos.filter(q_objects)

        repos = repos.order_by('-final_score')[:limit]
        serializer = self.get_serializer(repos, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def star(self, request, pk=None):
        repo = self.get_object()
        watch, created = RepositoryWatch.objects.get_or_create(user=request.user, repository=repo)
        return Response({
            'starred': True,
            'created': created,
            'repository_id': repo.id,
            'watch_id': watch.id,
        })

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def unstar(self, request, pk=None):
        repo = self.get_object()
        deleted, _ = RepositoryWatch.objects.filter(user=request.user, repository=repo).delete()
        return Response({
            'starred': False,
            'deleted': bool(deleted),
            'repository_id': repo.id,
        })
class superusercreate(APIView):
    def post(self, request):
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser("admin", "admin@example.com", "YourSecurePassword123")
            return Response({
                "message": "Admin created successfully!"
            })  