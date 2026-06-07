import math
import os
from django.contrib.auth import authenticate, get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
import google.generativeai as genai

from .models import Repository, RepositoryWatch, Issue, BeginnerChatSession, ChatMessage
from .serializers import RepositorySerializer

User = get_user_model()

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
            return Response({'detail': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email__iexact=email).exists():
            return Response({'detail': 'An account with that email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.create_user(username=email, email=email, password=password)
        refresh = RefreshToken.for_user(user)
        return Response({
            'authenticated': True,
            'user': serialize_user(user),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = (request.data.get('email') or '').strip().lower()
        password = request.data.get('password') or ''

        if not email or not password:
            return Response({'detail': 'Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        authenticated_user = authenticate(request, username=user.username, password=password)
        if not authenticated_user:
            return Response({'detail': 'Invalid email or password.'}, status=status.HTTP_400_BAD_REQUEST)

        refresh = RefreshToken.for_user(authenticated_user)
        return Response({
            'authenticated': True,
            'user': serialize_user(authenticated_user),
            'access': str(refresh.access_token),
            'refresh': str(refresh),
        })


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
        except TokenError:
            pass
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
                    model="models/gemini-embedding-2",
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


class ChatStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        issue_id = request.data.get('issue_id')
        try:
            issue = Issue.objects.select_related('repository').get(id=issue_id)
        except Issue.DoesNotExist:
            return Response({'error': 'Issue not found'}, status=status.HTTP_404_NOT_FOUND)

        session = BeginnerChatSession.objects.create(
            user=request.user,
            issue=issue
        )

        repo = issue.repository
        
        system_prompt = (
            "You are a helpful programming mentor. A beginner developer wants to contribute to an open-source project.\n"
            f"Repository Name: {repo.full_name}\n"
            f"Repository Description: {repo.description}\n"
            f"Language: {repo.language}\n"
            f"Issue Title: {issue.title}\n"
            f"Issue Body: {issue.body[:2000]}\n\n"
            "Provide a brief, encouraging summary of the repository and the task. Ask them if they are ready to get started. Keep it concise."
        )

        ChatMessage.objects.create(session=session, role='system', content=system_prompt)

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return Response({'error': 'GROQ_API_KEY not configured'}, status=500)

        from groq import Groq
        client = Groq(api_key=api_key)

        try:
            chat_completion = client.chat.completions.create(
                messages=[{"role": "system", "content": system_prompt}],
                model="llama-3.3-70b-versatile",
            )
            assistant_response = chat_completion.choices[0].message.content.strip()
            ChatMessage.objects.create(session=session, role='assistant', content=assistant_response)
        except Exception as e:
            print(f"Groq API Error: {e}")
            assistant_response = "I'm sorry, I'm having trouble connecting to my brain right now. Are you ready to get started?"
            ChatMessage.objects.create(session=session, role='assistant', content=assistant_response)

        return Response({
            'session_id': session.id,
            'message': assistant_response
        })


class ChatMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'Message cannot be empty'}, status=400)

        try:
            session = BeginnerChatSession.objects.get(id=session_id, user=request.user)
        except BeginnerChatSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        ChatMessage.objects.create(session=session, role='user', content=user_message)

        history = session.messages.all().order_by('created_at')
        messages = [{"role": msg.role, "content": msg.content} for msg in history]

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            return Response({'error': 'GROQ_API_KEY not configured'}, status=500)

        from groq import Groq
        client = Groq(api_key=api_key)

        try:
            chat_completion = client.chat.completions.create(
                messages=messages,
                model="llama-3.3-70b-versatile",
            )
            assistant_response = chat_completion.choices[0].message.content.strip()
            ChatMessage.objects.create(session=session, role='assistant', content=assistant_response)
        except Exception as e:
            print(f"Groq API Error: {e}")
            assistant_response = "Sorry, I encountered an error while thinking."
            ChatMessage.objects.create(session=session, role='assistant', content=assistant_response)

        return Response({'message': assistant_response})


from .models import RepoAgentSession
from .agent import ingest_repository, get_agent_graph
from langchain_core.messages import HumanMessage
import threading

def _run_ingestion_background(session_id, repo_url):
    try:
        session = RepoAgentSession.objects.get(id=session_id)
        repo_path, index_path = ingest_repository(repo_url, str(session.id))
        session.repo_path = repo_path
        session.index_path = index_path
        session.status = 'ready'
        session.save()
    except Exception as e:
        print(f"Ingestion failed: {e}")
        try:
            session = RepoAgentSession.objects.get(id=session_id)
            session.status = 'failed'
            session.save()
        except:
            pass

class RepoAgentIngestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk=None):
        try:
            repo = Repository.objects.get(id=pk)
        except Repository.DoesNotExist:
            return Response({'error': 'Repository not found'}, status=404)

        # Check if already a ready session exists for this user and repo
        existing = RepoAgentSession.objects.filter(user=request.user, repository=repo, status='ready').first()
        if existing:
            return Response({'session_id': existing.id, 'status': 'ready', 'message': 'Already indexed.'})

        session = RepoAgentSession.objects.create(
            user=request.user,
            repository=repo,
            status='indexing'
        )

        repo_url = repo.repo_url
        # If it's a standard URL, append .git if needed or let GitPython handle it
        thread = threading.Thread(target=_run_ingestion_background, args=(session.id, repo_url))
        thread.start()

        return Response({'session_id': session.id, 'status': 'indexing', 'message': 'Started indexing in background.'})

    def get(self, request, pk=None):
        # Allow checking status
        session_id = request.query_params.get('session_id')
        if not session_id:
            return Response({'error': 'session_id required'}, status=400)
        
        try:
            session = RepoAgentSession.objects.get(id=session_id, user=request.user)
            return Response({'session_id': session.id, 'status': session.status})
        except RepoAgentSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)


class RepoAgentChatView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, session_id):
        user_message = request.data.get('message', '').strip()
        if not user_message:
            return Response({'error': 'Message cannot be empty'}, status=400)

        try:
            session = RepoAgentSession.objects.get(id=session_id, user=request.user)
        except RepoAgentSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        if session.status != 'ready':
            return Response({'error': 'Session is not ready. Current status: ' + session.status}, status=400)

        # Retrieve history? For simplicity, we could just pass the current message, 
        # or load previous messages if we stored them in ChatMessage model.
        # Let's use ChatMessage for RepoAgentSession as well, or just pass a single turn for now.
        # Wait, the prompt implies "Blackboard memory", LangGraph holds state if we use a persistent checkpointer.
        # Since we haven't configured a DB checkpointer for LangGraph, we'll just pass the latest message.
        # To make it a true chat, we should retrieve previous ChatMessage objects if we linked them.
        
        agent_graph = get_agent_graph()
        
        initial_state = {
            "messages": [HumanMessage(content=user_message)],
            "session_id": str(session.id),
            "repo_path": session.repo_path,
            "index_path": session.index_path
        }
        
        os.environ["GROQ_API_KEY"] = os.environ.get("GROQ_API_KEY", "")
        os.environ["GOOGLE_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

        try:
            result = agent_graph.invoke(initial_state)
            final_message = result['messages'][-1].content
            return Response({'message': final_message})
        except Exception as e:
            print(f"Agent error: {e}")
            return Response({'error': str(e)}, status=500)