from django.contrib import admin
from django.contrib.admin import AdminSite
from django.contrib.auth.models import User, Group
from .models import PDFDocument, PDFSummary, ConversationThread, Question, Answer, PDFChunk

# Custom admin site with restricted access
class EasyLearningAdminSite(AdminSite):
    site_header = 'EasyLearning Administration'
    site_title = 'EasyLearning Admin'
    index_title = 'Welcome to EasyLearning Administration'
    
    def has_permission(self, request):
        """
        Only superusers can access the admin site
        """
        return request.user.is_active and request.user.is_superuser

# Create custom admin site instance
admin_site = EasyLearningAdminSite(name='easylearning_admin')

# Register models with custom admin site
@admin.register(PDFDocument)
class PDFDocumentAdmin(admin.ModelAdmin):
    list_display = ('title', 'uploaded_by', 'uploaded_at', 'file')
    list_filter = ('uploaded_at', 'uploaded_by')
    search_fields = ('title', 'uploaded_by__username')
    readonly_fields = ('uploaded_at',)
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(PDFSummary)
class PDFSummaryAdmin(admin.ModelAdmin):
    list_display = ('pdf_document', 'generated_at')
    list_filter = ('generated_at',)
    search_fields = ('pdf_document__title',)
    readonly_fields = ('generated_at',)
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ('title', 'pdf_document', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('title', 'pdf_document__title')
    readonly_fields = ('created_at', 'updated_at')
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('question_text', 'language', 'thread', 'asked_by', 'asked_at')
    list_filter = ('language', 'asked_at', 'asked_by')
    search_fields = ('question_text', 'thread__title', 'asked_by__username')
    readonly_fields = ('asked_at',)
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'language', 'is_from_pdf', 'confidence_score', 'generated_at')
    list_filter = ('language', 'is_from_pdf', 'confidence_score', 'generated_at')
    search_fields = ('answer_text', 'question__question_text')
    readonly_fields = ('generated_at',)
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

@admin.register(PDFChunk)
class PDFChunkAdmin(admin.ModelAdmin):
    list_display = ('pdf_document', 'chunk_index', 'text_preview')
    list_filter = ('pdf_document', 'chunk_index')
    search_fields = ('chunk_text', 'pdf_document__title')
    
    def text_preview(self, obj):
        return obj.chunk_text[:100] + '...' if len(obj.chunk_text) > 100 else obj.chunk_text
    text_preview.short_description = 'Text Preview'
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

# Register with custom admin site
admin_site.register(PDFDocument, PDFDocumentAdmin)
admin_site.register(PDFSummary, PDFSummaryAdmin)
admin_site.register(ConversationThread, ConversationThreadAdmin)
admin_site.register(Question, QuestionAdmin)
admin_site.register(Answer, AnswerAdmin)
admin_site.register(PDFChunk, PDFChunkAdmin)

# Register User and Group models for superuser management
admin_site.register(User)
admin_site.register(Group)
