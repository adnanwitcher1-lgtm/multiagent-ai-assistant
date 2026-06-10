from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.shortcuts import get_object_or_404
from django.core.files.uploadedfile import UploadedFile
from .models import User, ChatSession, Task
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    ChatSessionSerializer, TaskSerializer
)
import asyncio
import threading
import PyPDF2
from .agents import planner_agent, coder_agent, reviewer_agent

active_tasks = {}

def extract_text_from_file(file: UploadedFile) -> tuple:
    filename = file.name
    content = ""
    
    try:
        if filename.endswith('.pdf'):
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                content += page.extract_text()
        elif filename.endswith('.txt'):
            content = file.read().decode('utf-8')
        elif filename.endswith(('.png', '.jpg', '.jpeg')):
            content = f"[Image uploaded: {filename}]"
        else:
            content = f"[File uploaded: {filename}]"
    except Exception as e:
        content = f"[Error reading file: {str(e)}]"
    
    return filename, content

# ==================== AUTHENTICATION VIEWS ====================

class RegisterView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            refresh = RefreshToken.for_user(user)
            
            session, created = ChatSession.objects.get_or_create(
                user=user,
                is_active=True,
                defaults={'title': 'New Chat'}
            )
            
            return Response({
                'user': UserSerializer(user).data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'current_session': ChatSessionSerializer(session).data
            })
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

class LogoutView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except Exception:
            return Response({'message': 'Logged out'}, status=status.HTTP_200_OK)

class UserProfileView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)
        return Response({'message': 'Not logged in'}, status=status.HTTP_200_OK)

# ==================== CHAT SESSION VIEWS ====================

class ChatSessionListView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        if request.user.is_authenticated:
            sessions = ChatSession.objects.filter(user=request.user)
        else:
            sessions = ChatSession.objects.filter(user=None)
        return Response(ChatSessionSerializer(sessions, many=True).data)
    
    def post(self, request):
        title = request.data.get('title', 'New Chat')
        user = request.user if request.user.is_authenticated else None
        session = ChatSession.objects.create(user=user, title=title)
        return Response(ChatSessionSerializer(session).data, status=status.HTTP_201_CREATED)

class ChatSessionDetailView(APIView):
    permission_classes = [AllowAny]
    
    def delete(self, request, session_id):
        if request.user.is_authenticated:
            session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        else:
            session = get_object_or_404(ChatSession, session_id=session_id, user=None)
        session.delete()
        return Response({'message': 'Session deleted'})
    
    def put(self, request, session_id):
        if request.user.is_authenticated:
            session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        else:
            session = get_object_or_404(ChatSession, session_id=session_id, user=None)
        session.title = request.data.get('title', session.title)
        session.save()
        return Response(ChatSessionSerializer(session).data)

class SessionTasksView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, session_id):
        if request.user.is_authenticated:
            session = get_object_or_404(ChatSession, session_id=session_id, user=request.user)
        else:
            session = get_object_or_404(ChatSession, session_id=session_id, user=None)
        tasks = session.tasks.all()
        return Response(TaskSerializer(tasks, many=True).data)

# ==================== TASK/RUN VIEWS ====================

class RunTaskView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        try:
            prompt = request.data.get('task', '').strip()
            
            if not prompt:
                return Response({'error': 'Task prompt is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            if len(prompt) < 10:
                return Response({'error': 'Task must be at least 10 characters'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            if len(prompt) > 2000:
                return Response({'error': 'Task must be less than 2000 characters'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            # Create session and task
            user = request.user if request.user.is_authenticated else None
            session = ChatSession.objects.create(user=user, title='New Chat')
            
            task = Task.objects.create(
                session=session,
                user=user,
                prompt=prompt,
                status='pending'
            )
            
            # Run agents in background
            def run_agents():
                try:
                    task.status = 'running'
                    task.save()
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    try:
                        # Planner
                        task.status = 'planning'
                        task.save()
                        plan = loop.run_until_complete(planner_agent(prompt))
                        task.plan = plan
                        task.save()
                        
                        # Coder
                        task.status = 'coding'
                        task.save()
                        code = loop.run_until_complete(coder_agent(prompt, plan))
                        task.code = code
                        task.save()
                        
                        # Reviewer
                        task.status = 'reviewing'
                        task.save()
                        final = loop.run_until_complete(reviewer_agent(prompt, plan, code))
                        task.final_code = final
                        task.status = 'done'
                        task.save()
                        
                    finally:
                        loop.close()
                    
                    # Update session title
                    session.title = prompt[:40] + ('...' if len(prompt) > 40 else '')
                    session.save()
                    
                except Exception as e:
                    task.status = 'error'
                    task.error_message = str(e)
                    task.save()
                    print(f"Error in agents: {e}")
            
            thread = threading.Thread(target=run_agents)
            thread.daemon = True
            thread.start()
            active_tasks[str(task.task_id)] = thread
            
            return Response({
                'task_id': str(task.task_id),
                'session_id': str(session.session_id),
                'status': task.status
            }, status=status.HTTP_202_ACCEPTED)
            
        except Exception as e:
            print(f"Error in RunTaskView: {e}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

class TaskResultView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, task_id):
        task = get_object_or_404(Task, task_id=task_id)
        return Response(TaskSerializer(task).data)

class CancelTaskView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, task_id):
        task = get_object_or_404(Task, task_id=task_id)
        
        if task.status in ['done', 'error', 'cancelled']:
            return Response({'error': 'Task already completed'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        task.is_cancelled = True
        task.status = 'cancelled'
        task.save()
        
        return Response({'message': 'Task cancelled successfully'})