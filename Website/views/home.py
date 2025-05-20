from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.utils.timezone import now, timedelta, datetime
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from django.db.models import Avg, Max, Min
from django.db.models.functions import TruncHour
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

import base64
import json
import os

import logging

from ..models import SensorData, SensorLocation, Group
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from ..serializers import IncomingDataSerializer, SensorDataSerializer
from django.db import transaction

from Website.models import *
from Website.forms import *

logger = logging.getLogger('Website')

def handler404(request, exception):
    request_id = str(uuid.uuid4())
    logger.warning(f"[{request_id}] 404 Not Found: URL={request.path}, User={request.user if request.user.is_authenticated else 'Anonymous'}")
    return redirect('login')


def login_view(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting login_view. Method={request.method}, User Authenticated={request.user.is_authenticated}")

    if request.user.is_authenticated:
        logger.info(f"[{request_id}] User {request.user} already authenticated, redirecting to statuses.")
        return redirect('statuses')
    
    if request.method == 'POST':
        logger.debug(f"[{request_id}] Processing POST data for login: {request.POST}")
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            logger.info(f"[{request_id}] User {user} logged in successfully.")
            return redirect('statuses')
        else:
            logger.warning(f"[{request_id}] Login failed for POST data. Errors={form.errors}")
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        logger.debug(f"[{request_id}] Rendering empty login form.")
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})


def guest_login(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting guest_login. Method={request.method}, User Authenticated={request.user.is_authenticated}")

    if request.user.is_authenticated:
        logger.info(f"[{request_id}] User {request.user} already authenticated, redirecting to statuses.")
        return redirect('statuses')
    
    try:
        guest_user = User.objects.get(username="invite")
        login(request, guest_user)
        logger.info(f"[{request_id}] Guest user {guest_user} logged in successfully.")
        return redirect('statuses')
    except User.DoesNotExist:
        logger.error(f"[{request_id}] Guest user 'invite' does not exist.")
        messages.error(request, "L'utilisateur invité n'existe pas.")
        return redirect('login')


def logout_view(request):
    request_id = str(uuid.uuid4())
    logger.info(f"[{request_id}] User {request.user} logging out.")
    logout(request)
    return redirect('login')

DEFAULT_GROUP_NAME = "Non Assigné"

def is_admin(user):
    return user.is_superuser or user.is_staff

def home_page(request):
    return render(request, 'home.html')

@login_required(login_url='login')
def statuses_page(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting statuses_page. User={request.user}, Method={request.method}")
    user = request.user

    try:
        if user.is_superuser or user.is_staff:
            logger.debug(f"[{request_id}] {user} is admin/staff. Fetching all active raspberries.")
            raspberries = Raspberry.objects.filter(active=True).annotate(
                last_data=Max('sensor_locations__sensor_data__timestamp')
            )
        else:
            logger.debug(f"[{request_id}] {user} is standard user. Fetching raspberries by group.")
            user_groups = Group.objects.filter(user_groups__user=user)
            if not user_groups.exists():
                logger.warning(f"[{request_id}] {user} has no associated groups.")
                return render(request, 'statuses.html', {
                    'raspberries': [],
                    'error': "Vous n'êtes associé à aucun groupe.",
                })
            raspberries = Raspberry.objects.filter(group__in=user_groups, active=True).annotate(
                last_data=Max('sensor_locations__sensor_data__timestamp')
            )

        current_time = now()
        raspberry_status = []
        for raspberry in raspberries:
            if raspberry.last_data and raspberry.last_data >= current_time - timedelta(hours=1):
                status = "En ligne"
            else:
                status = "Hors ligne"
            raspberry_status.append({
                'id': raspberry.id,
                'device_id': raspberry.device_id,
                'group': raspberry.group.name if raspberry.group else "Non Assigné",
                'location': raspberry.location_description or "Non spécifié",
                'status': status,
                'last_data': (raspberry.last_data + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S') if raspberry.last_data else "Aucune donnée",
            })

        logger.info(f"[{request_id}] Rendered statuses_page for User={user} with {len(raspberry_status)} raspberries.")
        return render(request, 'statuses.html', {
            'raspberry_status': raspberry_status,
        })
    except Exception as e:
        logger.exception(f"[{request_id}] Error rendering statuses_page for User={user}: {e}")
        return render(request, 'statuses.html', {
            'raspberries': [],
            'error': "Une erreur s'est produite lors de la récupération des données.",
        })