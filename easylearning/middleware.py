from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse

class AdminAccessMiddleware:
    """
    Middleware to restrict admin access to superusers only
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user is trying to access admin site
        if request.path.startswith('/admin/'):
            # Allow access only if user is superuser
            if not request.user.is_authenticated:
                # Not logged in, let Django handle the redirect to login
                pass
            elif not request.user.is_superuser:
                # Logged in but not superuser, redirect to home
                messages.error(request, 'Access denied. Admin panel is only available to administrators.')
                return redirect('easylearning:landing')
        
        response = self.get_response(request)
        return response 