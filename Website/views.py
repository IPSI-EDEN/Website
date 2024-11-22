from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.db.models import Sum, Count

from Website.models import *

def handler404(request, exception):
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home_page')
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)

        if user is None:
            messages.error(request, "Utilisateur inconnu ou mot de passe incorrect")
            return render(request, 'registration/login.html', {'form': AuthenticationForm()})
        else:
            login(request, user)
            return redirect('home_page')
    
    return render(request, 'registration/login.html', {'form': AuthenticationForm()})

def logout_view(request):
    logout(request)
    return redirect('login')

def home_page(request):
    if request.user.is_authenticated:
        return render(request, 'home.html')
    return redirect('login')