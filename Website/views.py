from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages

import plotly.graph_objs as go
import plotly.express as px
import plotly
import json

from Website.models import *

def handler404(request, exception):
    return redirect('login')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
    else:
        form = AuthenticationForm()
    
    return render(request, 'registration/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "Vous avez été déconnecté avec succès.")
    return redirect('login')

@login_required(login_url='login')
def home_page(request):
    # Données d'exemple (remplacez-les par vos données réelles)
    temperature_data = [22, 23, 21, 24, 25]
    humidity_data = [55, 60, 58, 62, 59]
    moist_data = [40, 42, 38, 45, 43]
    water_level = [80]  # Par exemple, niveau d'eau actuel
    voltage_data = [220, 221, 219, 222, 223]
    power_data = [100, 105, 102, 110, 108]
    time_labels = ['08:00', '10:00', '12:00', '14:00', '16:00']

    # Créer des graphiques de ligne avec Plotly Express
    temperature_chart = px.line(
        x=time_labels, y=temperature_data,
        labels={'x': 'Heure', 'y': 'Température (°C)'},
        title='Température au fil du temps'
    )
    humidity_chart = px.line(
        x=time_labels, y=humidity_data,
        labels={'x': 'Heure', 'y': 'Humidité (%)'},
        title='Humidité au fil du temps'
    )
    moist_chart = px.line(
        x=time_labels, y=moist_data,
        labels={'x': 'Heure', 'y': 'Humidité du sol (%)'},
        title='Humidité du sol au fil du temps'
    )
    voltage_chart = px.line(
        x=time_labels, y=voltage_data,
        labels={'x': 'Heure', 'y': 'Tension (V)'},
        title='Tension consommée au fil du temps'
    )
    power_chart = px.line(
        x=time_labels, y=power_data,
        labels={'x': 'Heure', 'y': 'Puissance (W)'},
        title='Puissance reçue au fil du temps'
    )

    # Convertir les graphiques en JSON
    temperature_chart_json = json.dumps(temperature_chart, cls=plotly.utils.PlotlyJSONEncoder)
    humidity_chart_json = json.dumps(humidity_chart, cls=plotly.utils.PlotlyJSONEncoder)
    moist_chart_json = json.dumps(moist_chart, cls=plotly.utils.PlotlyJSONEncoder)
    voltage_chart_json = json.dumps(voltage_chart, cls=plotly.utils.PlotlyJSONEncoder)
    power_chart_json = json.dumps(power_chart, cls=plotly.utils.PlotlyJSONEncoder)

    # Créer des jauges avec Plotly Graph Objects
    temperature_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=temperature_data[-1],
        title={'text': "Température actuelle"},
        gauge={'axis': {'range': [0, 50]}}
    ))
    temperature_gauge_json = json.dumps(temperature_gauge, cls=plotly.utils.PlotlyJSONEncoder)

    humidity_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=humidity_data[-1],
        title={'text': "Humidité actuelle"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    humidity_gauge_json = json.dumps(humidity_gauge, cls=plotly.utils.PlotlyJSONEncoder)

    moist_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=moist_data[-1],
        title={'text': "Humidité du sol actuelle"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    moist_gauge_json = json.dumps(moist_gauge, cls=plotly.utils.PlotlyJSONEncoder)

    water_level_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=water_level[-1],
        title={'text': "Niveau d'eau dans la cuve"},
        gauge={'axis': {'range': [0, 100]}}
    ))
    water_level_gauge_json = json.dumps(water_level_gauge, cls=plotly.utils.PlotlyJSONEncoder)

    # Préparer les contextes pour les jauges
    gauges = [
        {'title': 'Température', 'id': 'temperatureGauge', 'json': temperature_gauge_json},
        {'title': 'Humidité', 'id': 'humidityGauge', 'json': humidity_gauge_json},
        {'title': 'Humidité du sol', 'id': 'moistGauge', 'json': moist_gauge_json},
        {'title': "Niveau d'eau dans la cuve", 'id': 'waterLevelGauge', 'json': water_level_gauge_json},
    ]

    # Préparer les contextes pour les graphiques
    charts_top = [
        {'title': 'Température', 'id': 'temperatureChart', 'json': temperature_chart_json},
    ]

    charts_middle = [
        {'title': 'Humidité', 'id': 'humidityChart', 'json': humidity_chart_json},
        {'title': 'Humidité du sol', 'id': 'moistChart', 'json': moist_chart_json},
    ]

    charts_bottom = [
        {'title': 'Puissance consommée', 'id': 'voltageChart', 'json': voltage_chart_json},
        {'title': 'Puissance reçue', 'id': 'powerChart', 'json': power_chart_json},
    ]

    water_charts = charts_middle  # Réutilisation pour l'affichage mobile

    final_charts = charts_bottom  # Réutilisation pour l'affichage mobile

    context = {
        'gauges': gauges,
        'charts_top': charts_top,
        'charts_middle': charts_middle,
        'charts_bottom': charts_bottom,
        'water_charts': water_charts,
        'final_charts': final_charts,
    }

    return render(request, 'home.html', context)
