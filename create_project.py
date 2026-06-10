# create_project.py
import os

PROJECT_PATH = r"D:\AI agent\multiagent-ai"

def create_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ {path}")

# Backend Files
create_file(f"{PROJECT_PATH}/backend/requirements.txt", """django==5.0.6
djangorestframework==3.15.2
django-cors-headers==4.3.1
celery==5.3.6
redis==5.0.4
openai==1.30.1
langgraph==0.2.4
langchain==0.2.6
langchain-openai==0.1.14
python-dotenv==1.0.1""")

create_file(f"{PROJECT_PATH}/backend/.env", """OPENAI_API_KEY=your_key_here
REDIS_URL=redis://localhost:6379/0""")

create_file(f"{PROJECT_PATH}/backend/manage.py", """#!/usr/bin/env python
import os, sys

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError("Couldn't import Django") from exc
    execute_from_command_line(sys.argv)

if __name__ == '__main__':
    main()""")

create_file(f"{PROJECT_PATH}/backend/backend/__init__.py", "from .celery import app as celery_app\n\n__all__ = ('celery_app',)")
create_file(f"{PROJECT_PATH}/backend/backend/celery.py", """import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
app = Celery('backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()""")

create_file(f"{PROJECT_PATH}/backend/backend/wsgi.py", """import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
application = get_wsgi_application()""")

create_file(f"{PROJECT_PATH}/backend/backend/settings.py", """import os
from pathlib import Path
from dotenv import load_dotenv
from django.core.exceptions import ImproperlyConfigured

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = 'django-insecure-key'
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'rest_framework', 'corsheaders', 'api',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'
WSGI_APPLICATION = 'backend.wsgi.application'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
CORS_ALLOW_ALL_ORIGINS = True

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    raise ImproperlyConfigured("OPENAI_API_KEY missing in .env file")

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL""")

create_file(f"{PROJECT_PATH}/backend/backend/urls.py", """from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
]""")

create_file(f"{PROJECT_PATH}/backend/api/__init__.py", "")
create_file(f"{PROJECT_PATH}/backend/api/migrations/__init__.py", "")

create_file(f"{PROJECT_PATH}/backend/api/models.py", """import uuid
from django.db import models

class Task(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'), ('running', 'Running'), ('planning', 'Planning'),
        ('coding', 'Coding'), ('reviewing', 'Reviewing'), ('done', 'Done'), ('error', 'Error'),
    ]
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt = models.TextField()
    plan = models.TextField(blank=True, default='')
    code = models.TextField(blank=True, default='')
    final_code = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']""")

create_file(f"{PROJECT_PATH}/backend/api/admin.py", """from django.contrib import admin
from .models import Task

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'status', 'created_at']""")

create_file(f"{PROJECT_PATH}/backend/api/apps.py", """from django.apps import AppConfig

class ApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'""")

create_file(f"{PROJECT_PATH}/backend/api/serializers.py", """from rest_framework import serializers
from .models import Task

class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = Task
        fields = '__all__'

class TaskListSerializer(serializers.ModelSerializer):
    prompt_preview = serializers.SerializerMethodField()
    
    class Meta:
        model = Task
        fields = ['task_id', 'prompt_preview', 'status', 'created_at']
    
    def get_prompt_preview(self, obj):
        return obj.prompt[:60] + ('...' if len(obj.prompt) > 60 else '')""")

create_file(f"{PROJECT_PATH}/backend/api/views.py", """from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import Task
from .serializers import TaskSerializer, TaskListSerializer
from .tasks import run_agent_pipeline

class RunTaskView(APIView):
    def post(self, request):
        prompt = request.data.get('task', '').strip()
        if not prompt or len(prompt) < 10 or len(prompt) > 2000:
            return Response({'error': 'Invalid task length'}, status=status.HTTP_400_BAD_REQUEST)
        task = Task.objects.create(prompt=prompt, status='pending')
        run_agent_pipeline.delay(str(task.task_id), prompt)
        return Response({'task_id': str(task.task_id), 'status': task.status}, status=status.HTTP_202_ACCEPTED)

class TaskResultView(APIView):
    def get(self, request, task_id):
        task = get_object_or_404(Task, task_id=task_id)
        return Response(TaskSerializer(task).data)

class TaskHistoryView(APIView):
    def get(self, request):
        tasks = Task.objects.all()[:20]
        return Response(TaskListSerializer(tasks, many=True).data)""")

create_file(f"{PROJECT_PATH}/backend/api/urls.py", """from django.urls import path
from . import views

urlpatterns = [
    path('run/', views.RunTaskView.as_view()),
    path('result/<uuid:task_id>/', views.TaskResultView.as_view()),
    path('tasks/', views.TaskHistoryView.as_view()),
]""")

create_file(f"{PROJECT_PATH}/backend/api/agents.py", """import re
from langchain_openai import ChatOpenAI
from django.conf import settings

llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0.7, api_key=settings.OPENAI_API_KEY)

def strip_markdown(text):
    text = re.sub(r'^```\\w*\\n', '', text, flags=re.MULTILINE)
    text = re.sub(r'\\n```$', '', text.strip(), flags=re.MULTILINE)
    return text.strip()

async def planner_agent(prompt):
    response = await llm.ainvoke([
        {"role": "system", "content": "You are an expert architect. Produce step-by-step plan. No code. Max 300 words."},
        {"role": "user", "content": f"Task: {prompt}"}
    ])
    return strip_markdown(response.content)

async def coder_agent(prompt, plan):
    response = await llm.ainvoke([
        {"role": "system", "content": "You are a senior engineer. Write complete production code. Return ONLY raw code."},
        {"role": "user", "content": f"Task: {prompt}\\n\\nPlan: {plan}\\n\\nWrite code:"}
    ])
    return strip_markdown(response.content)

async def reviewer_agent(prompt, plan, code):
    response = await llm.ainvoke([
        {"role": "system", "content": "You are a reviewer. Fix all bugs. Return ONLY final corrected code."},
        {"role": "user", "content": f"Task: {prompt}\\n\\nPlan: {plan}\\n\\nCode: {code}\\n\\nFixed code:"}
    ])
    return strip_markdown(response.content)""")

create_file(f"{PROJECT_PATH}/backend/api/tasks.py", """import asyncio
from celery import shared_task
from django.db import transaction
from .models import Task
from .agents import planner_agent, coder_agent, reviewer_agent

@shared_task(bind=True)
def run_agent_pipeline(self, task_id, prompt):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        Task.objects.filter(task_id=task_id).update(status='planning')
        plan = loop.run_until_complete(planner_agent(prompt))
        
        Task.objects.filter(task_id=task_id).update(plan=plan, status='coding')
        code = loop.run_until_complete(coder_agent(prompt, plan))
        
        Task.objects.filter(task_id=task_id).update(code=code, status='reviewing')
        final = loop.run_until_complete(reviewer_agent(prompt, plan, code))
        
        Task.objects.filter(task_id=task_id).update(final_code=final, status='done')
        loop.close()
    except Exception as e:
        Task.objects.filter(task_id=task_id).update(status='error', error_message=str(e))
        raise""")

# Frontend Files
create_file(f"{PROJECT_PATH}/frontend/package.json", """{
  "name": "ai-coder",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {"dev": "vite", "build": "vite build"},
  "dependencies": {
    "react": "^18.2.0", "react-dom": "^18.2.0",
    "react-syntax-highlighter": "^15.5.0", "axios": "^1.6.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.2.1", "autoprefixer": "^10.4.16",
    "postcss": "^8.4.32", "tailwindcss": "^3.3.6", "vite": "^5.0.8"
  }
}""")

create_file(f"{PROJECT_PATH}/frontend/vite.config.js", """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { port: 3000, proxy: { '/api': { target: 'http://localhost:8000', changeOrigin: true } } }
})""")

create_file(f"{PROJECT_PATH}/frontend/tailwind.config.js", """export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: { colors: { 'cyan-accent': '#00d4ff', 'dark-bg': '#0a0a0f' } } },
  plugins: []
}""")

create_file(f"{PROJECT_PATH}/frontend/postcss.config.js", "export default { plugins: { tailwindcss: {}, autoprefixer: {} } }")
create_file(f"{PROJECT_PATH}/frontend/index.html", """<!DOCTYPE html>
<html><head><meta charset="UTF-8" /><title>Multi-Agent AI Coder</title>
<link href="https://fonts.googleapis.com/css2?family=Inter&family=JetBrains+Mono&display=swap" rel="stylesheet">
</head><body><div id="root"></div><script type="module" src="/src/main.jsx"></script></body></html>""")

create_file(f"{PROJECT_PATH}/frontend/src/index.css", """@tailwind base;@tailwind components;@tailwind utilities;
@layer base { body { @apply bg-dark-bg text-gray-100 font-sans; } }
@layer utilities { .glass { @apply bg-gray-900/50 backdrop-blur-sm border border-gray-800; } }""")

create_file(f"{PROJECT_PATH}/frontend/src/main.jsx", """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
ReactDOM.createRoot(document.getElementById('root')).render(<React.StrictMode><App /></React.StrictMode>)""")

create_file(f"{PROJECT_PATH}/frontend/src/App.jsx", """import React, { useState, useEffect, useCallback, useRef } from 'react';
import axios from 'axios';

const API = axios.create({ baseURL: '/api' });

function App() {
  const [prompt, setPrompt] = useState('');
  const [taskData, setTaskData] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [toasts, setToasts] = useState([]);
  const pollingRef = useRef(null);

  const addToast = (msg, type='error') => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, msg, type }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000);
  };

  const stopPolling = useCallback(() => {
    if (pollingRef.current) { clearInterval(pollingRef.current); pollingRef.current = null; }
  }, []);

  const fetchResult = useCallback(async (taskId) => {
    try {
      const { data } = await API.get(`/result/${taskId}/`);
      setTaskData(data);
      if (data.status === 'done' || data.status === 'error') {
        stopPolling();
        setIsRunning(false);
        addToast(data.status === 'done' ? 'Task completed!' : `Error: ${data.error_message}`, data.status === 'done' ? 'success' : 'error');
      }
    } catch { addToast('Failed to fetch result'); stopPolling(); setIsRunning(false); }
  }, [stopPolling]);

  const startPolling = useCallback((taskId) => {
    stopPolling();
    pollingRef.current = setInterval(() => fetchResult(taskId), 2000);
  }, [fetchResult, stopPolling]);

  const runAgents = async () => {
    if (!prompt.trim() || isRunning) return;
    if (prompt.length < 10) return addToast('Task too short (min 10 chars)');
    setIsRunning(true);
    setTaskData(null);
    try {
      const { data } = await API.post('/run/', { task: prompt });
      startPolling(data.task_id);
    } catch (err) { addToast(err.response?.data?.error || 'Failed to start'); setIsRunning(false); }
  };

  useEffect(() => () => stopPolling(), [stopPolling]);

  const steps = [{name:'Planner',key:'planning'},{name:'Coder',key:'coding'},{name:'Reviewer',key:'reviewing'}];
  const getStepStatus = (key) => {
    if (!taskData) return 'idle';
    if (taskData.status === 'done') return 'done';
    if (taskData.status === key) return 'active';
    const order = ['planning','coding','reviewing'];
    if (order.indexOf(taskData.status) > order.indexOf(key)) return 'done';
    return 'idle';
  };

  return (
    <div className="min-h-screen bg-dark-bg">
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-4xl font-bold text-center bg-gradient-to-r from-cyan-accent to-purple-500 bg-clip-text text-transparent mb-2">⚡ Multi-Agent AI Coder</h1>
        <p className="text-center text-gray-400 mb-8">Three AI agents collaborating to write your code</p>
        
        <div className="glass rounded-xl p-6 mb-8">
          <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe what to build..." className="w-full h-32 bg-gray-900 border border-gray-700 rounded-lg p-4 text-white" disabled={isRunning} />
          <button onClick={runAgents} disabled={isRunning||!prompt.trim()} className="mt-4 px-6 py-3 bg-cyan-accent text-dark-bg font-semibold rounded-lg disabled:opacity-50">
            {isRunning ? '⏳ Running Agents...' : '⚡ Run Agents'}
          </button>
        </div>

        {taskData && (
          <>
            <div className="glass rounded-xl p-6 mb-8">
              <h3 className="text-lg font-semibold mb-4">Agent Progress</h3>
              <div className="flex justify-between">
                {steps.map((step,i)=>(
                  <div key={step.key} className="flex-1 text-center">
                    <div className={`w-12 h-12 rounded-full mx-auto mb-2 flex items-center justify-center ${getStepStatus(step.key)==='active'?'border-2 border-cyan-accent':getStepStatus(step.key)==='done'?'bg-green-500':'bg-gray-800'}`}>
                      {getStepStatus(step.key)==='active'&&<div className="w-3 h-3 bg-cyan-accent rounded-full animate-pulse"></div>}
                      {getStepStatus(step.key)==='done'&&<span>✓</span>}
                      {getStepStatus(step.key)==='idle'&&<span>○</span>}
                    </div>
                    <span className={`text-sm ${getStepStatus(step.key)==='active'?'text-cyan-accent':getStepStatus(step.key)==='done'?'text-green-500':'text-gray-500'}`}>{step.name}</span>
                  </div>
                ))}
              </div>
            </div>

            {taskData.plan && <div className="glass rounded-xl p-6 mb-6"><h3 className="text-lg font-semibold mb-2">📋 Plan</h3><pre className="font-mono text-sm whitespace-pre-wrap">{taskData.plan}</pre></div>}
            {taskData.code && <div className="glass rounded-xl p-6 mb-6"><h3 className="text-lg font-semibold mb-2">💻 Code</h3><pre className="font-mono text-sm overflow-x-auto">{taskData.code}</pre></div>}
            {taskData.final_code && <div className="glass rounded-xl p-6"><h3 className="text-lg font-semibold mb-2">✅ Final Code</h3><button onClick={()=>{navigator.clipboard.writeText(taskData.final_code);addToast('Copied!','success');}} className="mb-2 px-3 py-1 bg-gray-800 rounded text-sm">📋 Copy</button><pre className="font-mono text-sm overflow-x-auto">{taskData.final_code}</pre></div>}
          </>
        )}
      </div>
      {toasts.map(t=><div key={t.id} className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg ${t.type==='success'?'bg-green-500':'bg-red-500'} text-white`}>{t.msg}</div>)}
    </div>
  );
}
export default App;""")

print("\n" + "="*50)
print("🎉 PROJECT CREATED SUCCESSFULLY!")
print("="*50)
print(f"\n📁 Location: {PROJECT_PATH}")
print("\n📝 Next Steps:")
print("1. Add your OpenAI API key to: backend/.env")
print("2. Open 3 terminals and run:")
print("\n   Terminal 1 (Redis): docker run -d -p 6379:6379 redis")
print("   Terminal 2 (Backend): cd backend && pip install -r requirements.txt && python manage.py migrate && python manage.py runserver")
print("   Terminal 3 (Celery): cd backend && celery -A backend worker -l info")
print("   Terminal 4 (Frontend): cd frontend && npm install && npm run dev")
print("\n🌐 Open: http://localhost:3000")