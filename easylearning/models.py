from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid


class PDFDocument(models.Model):
    """Model to store uploaded PDF documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.title


class PDFSummary(models.Model):
    """Model to store generated summaries of PDF documents"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_document = models.OneToOneField(PDFDocument, on_delete=models.CASCADE, related_name='summary')
    summary_text = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Summary of {self.pdf_document.title}"


class ConversationThread(models.Model):
    """Model to store conversation threads for each PDF"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='conversations')
    title = models.CharField(max_length=255, default="New Conversation")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.pdf_document.title}"


class Question(models.Model):
    """Model to store questions asked by users"""
    LANGUAGE_CHOICES = [
        ('en', 'English'),
        ('gu', 'Gujarati'),
        ('hi', 'Hindi'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(ConversationThread, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField()
    language = models.CharField(max_length=2, choices=LANGUAGE_CHOICES, default='en')
    asked_at = models.DateTimeField(auto_now_add=True)
    asked_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    def __str__(self):
        return self.question_text[:50]


class Answer(models.Model):
    """Model to store answers to questions"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    question = models.OneToOneField(Question, on_delete=models.CASCADE, related_name='answer')
    answer_text = models.TextField()
    language = models.CharField(max_length=2, choices=Question.LANGUAGE_CHOICES, default='en')
    is_from_pdf = models.BooleanField(default=True)
    confidence_score = models.FloatField(default=0.0)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Answer to: {self.question.question_text[:30]}"


class PDFChunk(models.Model):
    """Model to store PDF text chunks for better search and retrieval"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pdf_document = models.ForeignKey(PDFDocument, on_delete=models.CASCADE, related_name='chunks')
    chunk_text = models.TextField()
    chunk_index = models.IntegerField()
    page_number = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Chunk {self.chunk_index} of {self.pdf_document.title}"
