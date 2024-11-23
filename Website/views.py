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
    water_level = [80]  # Niveau d'eau actuel
    voltage_data = [220, 221, 219, 222, 223]
    power_data = [100, 105, 102, 110, 108]
    time_labels = ['08:00', '10:00', '12:00', '14:00', '16:00']

    # Définir la palette de couleurs
    colors = {
        'primary': '#0d6efd',
        'secondary': '#6c757d',
        'success': '#198754',
        'danger': '#dc3545',
        'warning': '#ffc107',
        'info': '#0dcaf0',
        'light': '#f8f9fa',
        'dark': '#212529',
    }

    # Créer un template Plotly personnalisé
    custom_template = go.layout.Template(
        layout=go.Layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            plot_bgcolor=colors['light'],
            colorway=[colors['primary'], colors['secondary'], colors['success'], colors['danger']],
            xaxis=dict(gridcolor=colors['secondary']),
            yaxis=dict(gridcolor=colors['secondary']),
            title=dict(x=0.5),
            margin=dict(l=10, r=10, t=50, b=50),
        )
    )

    # Créer les graphiques
    charts = []
    data_list = [
        {'data': temperature_data, 'title': 'Température au fil du temps', 'y_label': 'Température (°C)', 'id': 'temperatureChart', 'color': colors['primary']},
        {'data': humidity_data, 'title': 'Humidité au fil du temps', 'y_label': 'Humidité (%)', 'id': 'humidityChart', 'color': colors['info']},
        {'data': moist_data, 'title': 'Humidité du sol au fil du temps', 'y_label': 'Humidité du sol (%)', 'id': 'moistChart', 'color': colors['success']},
        {'data': voltage_data, 'title': 'Tension consommée au fil du temps', 'y_label': 'Tension (V)', 'id': 'voltageChart', 'color': colors['warning']},
        {'data': power_data, 'title': 'Puissance reçue au fil du temps', 'y_label': 'Puissance (W)', 'id': 'powerChart', 'color': colors['danger']},
    ]

    for item in data_list:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=time_labels,
            y=item['data'],
            mode='lines+markers',
            line=dict(color=item['color'], width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            # Retirer le titre du graphique
            # title=item['title'],
            xaxis_title='Heure',
            yaxis_title=item['y_label'],
            template=custom_template,
            autosize=True,
        )
        fig.update_layout(margin=dict(l=40, r=40, t=40, b=40))
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        charts.append({'title': item['title'], 'id': item['id'], 'json': fig_json})

    # Créer les jauges
    gauges = []
    gauge_data = [
        {'value': temperature_data[-1], 'title': 'Température actuelle', 'id': 'temperatureGauge', 'range': [0, 50], 'color': colors['primary']},
        {'value': humidity_data[-1], 'title': 'Humidité actuelle', 'id': 'humidityGauge', 'range': [0, 100], 'color': colors['info']},
        {'value': moist_data[-1], 'title': 'Humidité du sol actuelle', 'id': 'moistGauge', 'range': [0, 100], 'color': colors['success']},
        {'value': water_level[-1], 'title': "Niveau d'eau dans la cuve", 'id': 'waterLevelGauge', 'range': [0, 100], 'color': colors['warning']},
    ]

    for gauge in gauge_data:
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=gauge['value'],
            # Retirer le titre de la jauge
            # title={'text': gauge['title'], 'font': {'size': 14}},
            gauge={
                'axis': {'range': gauge['range'], 'tickwidth': 1, 'tickcolor': colors['dark']},
                'bar': {'color': gauge['color']},
                'bgcolor': colors['light'],
                'borderwidth': 1,
                'bordercolor': colors['secondary'],
            },
        ))
        fig.update_layout(
            font=dict(family="Arial, sans-serif", size=12, color=colors['dark']),
            paper_bgcolor=colors['light'],
            autosize=True,
            margin=dict(l=10, r=10, t=40, b=10),
        )
        fig_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
        gauges.append({'title': gauge['title'], 'id': gauge['id'], 'json': fig_json})

    context = {
        'gauges': gauges,
        'charts': charts,
    }

    return render(request, 'home.html', context)