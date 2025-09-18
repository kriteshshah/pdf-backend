from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('easylearning:home')
    
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in after registration
            login(request, user)
            messages.success(request, f'Welcome to EasyLearning, {user.username}! Your account has been created successfully.')
            return redirect('easylearning:home')
        else:
            # Display form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})


def login_view(request):
    """Custom login view"""
    if request.user.is_authenticated:
        return redirect('easylearning:home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.username}!')
            
            # Redirect to next page if specified
            next_page = request.GET.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect('easylearning:home')
        else:
            messages.error(request, 'Invalid username or password. Please try again.')
    
    return render(request, 'registration/login.html')


@login_required
def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('easylearning:home')


def password_reset_view(request):
    """Password reset view (placeholder)"""
    messages.info(request, 'Password reset functionality will be implemented soon.')
    return redirect('easylearning:login') 