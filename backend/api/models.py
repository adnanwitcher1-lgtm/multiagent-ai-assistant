# backend/api/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    """Custom User model"""
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
    
    @property
    def id(self):
        return self.user_id

    def __str__(self):
        return self.username

class ChatSession(models.Model):
    """Chat session for each user"""
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    title = models.CharField(max_length=200, default='New Chat')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class Task(models.Model):
    """Task/Message in a chat session"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('planning', 'Planning'),
        ('coding', 'Coding'),
        ('reviewing', 'Reviewing'),
        ('done', 'Done'),
        ('error', 'Error'),
        ('cancelled', 'Cancelled'),
    ]
    
    task_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # FIXED: Added null=True, blank=True to both foreign keys
    session = models.ForeignKey(
        ChatSession, 
        on_delete=models.CASCADE, 
        related_name='tasks',
        null=True,
        blank=True
    )
    
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='tasks',
        null=True,  # ✅ Allow null for existing rows
        blank=True   # ✅ Allow blank in forms
    )
    
    prompt = models.TextField()
    plan = models.TextField(blank=True, default='')
    code = models.TextField(blank=True, default='')
    final_code = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, default='')
    is_cancelled = models.BooleanField(default=False)
    file_name = models.CharField(max_length=255, blank=True, default='')
    file_content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.prompt[:50]} - {self.status}"