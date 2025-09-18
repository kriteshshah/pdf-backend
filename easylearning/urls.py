from django.urls import path
from . import views
from . import auth_views

app_name = 'easylearning'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('home/', views.home, name='home'),
    path('upload/', views.upload_pdf, name='upload_pdf'),
    path('pdf/<uuid:pdf_id>/', views.pdf_detail, name='pdf_detail'),
    path('pdf/<uuid:pdf_id>/create-thread/', views.create_thread, name='create_thread'),
    path('thread/<uuid:thread_id>/', views.thread_detail, name='thread_detail'),
    path('api/ask-question/', views.ask_question_api, name='ask_question_api'),
    
    # Authentication URLs
    path('login/', auth_views.login_view, name='login'),
    path('register/', auth_views.register_view, name='register'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('password-reset/', auth_views.password_reset_view, name='password_reset'),
    path('profile/', views.profile_view, name='profile'),
    path('test-dropdown/', views.test_dropdown_view, name='test_dropdown'),
] 