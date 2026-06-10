import asyncio
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
        raise