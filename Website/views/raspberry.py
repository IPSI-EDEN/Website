from .home import *

@login_required(login_url='login')
def manage_greenhouse(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
    plants = Plant.objects.all()

    # Préparation des données pour la visualisation D3.js
    sensor_locations_data = []
    for location in sensor_locations:
        sensor_locations_data.append({
            'location_name': location.location_name,
            'plant': {
                'name': location.plant.name,
                'soil_moisture_min': location.plant.soil_moisture_min,
                'soil_moisture_max': location.plant.soil_moisture_max,
            },
            'soil_moisture': location.soil_moisture,
            'x_position': location.x_position,
            'y_position': location.y_position,
        })

    # Création d'un formset pour gérer les formulaires de seuils des plantes
    PlantFormSet = modelformset_factory(Plant, form=PlantThresholdForm, extra=0)

    # Traitement spécifique pour le basculement des équipements
    if request.method == 'POST' and 'toggle_device' in request.POST:
        device = request.POST.get('toggle_device')
        if device == 'pump':
            raspberry.pump_state = not raspberry.pump_state
        elif device == 'fan':
            raspberry.fan_state = not raspberry.fan_state
        raspberry.save()
        messages.success(request, f"L'état de {device} a été modifié.")
        return redirect('raspberry_threshold', id=raspberry.id)

    # Traitement du formset pour les seuils
    if request.method == 'POST':
        formset = PlantFormSet(request.POST, queryset=plants)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Les seuils des plantes ont été mis à jour.")
            return redirect('threshold', id=raspberry.id)
    else:
        formset = PlantFormSet(queryset=plants)

    context = {
        'raspberry': raspberry,
        'formset': formset,
        'sensor_locations_json': json.dumps(sensor_locations_data),
    }
    return render(request, 'manage_greenhouse.html', context)

@login_required(login_url='login')
def graph_page(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)

    selected_time_range = int(request.GET.get('time_range', 24))
    end_time = now()
    start_time = end_time - timedelta(hours=selected_time_range)

    # On récupère l'ensemble des données pour ce Raspberry & la période
    sensor_data = SensorData.objects.filter(
        sensor_location__in=sensor_locations,
        timestamp__gte=start_time
    ).order_by('timestamp')

    # Prépare des listes vides par défaut
    temperature_data = []
    humidity_data = []
    water_level_data = []
    time_labels = []
    current_temperature = 0
    current_humidity = 0
    current_water_level = 0

    # -- NOUVEAU -- On va construire un dictionnaire pour regrouper les données d'humidité du sol
    # par "location" (= par capteur)
    soil_moisture_dict = {}  # clef = sensor_location.id, valeur = { 'name': x, 'timestamps': [], 'values': [] }

    for location in sensor_locations:
        soil_moisture_dict[location.id] = {
            'name': location.location_name,
            'timestamps': [],
            'values': []
        }

    if not sensor_data.exists():
        # Aucune donnée : toutes les listes restent vides
        pass
    else:
        # Limiter à MAX_POINTS pour éviter de surcharger les graphiques
        MAX_POINTS = 200
        total_points = sensor_data.count()
        if total_points > MAX_POINTS:
            step = total_points // MAX_POINTS
            sensor_ids = list(sensor_data.values_list('pk', flat=True))
            sensor_ids = sensor_ids[::step]  # On ne garde qu’un point sur "step"
            sensor_data = SensorData.objects.filter(pk__in=sensor_ids).order_by('timestamp')

        # On parcourt tous les SensorData pour alimenter les courbes
        for data in sensor_data:
            # Convertit le timestamp en chaîne pour l'axe X
            t_str = (data.timestamp + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')

            # Température/air_humidity/water_level restent uniques (on pourrait prendre la moyenne, etc.)
            temperature_data.append(data.temperature if data.temperature is not None else None)
            humidity_data.append(data.air_humidity if data.air_humidity is not None else None)

            if hasattr(data, 'water_level'):
                water_level_data.append(data.water_level if data.water_level is not None else None)
            else:
                water_level_data.append(None)

            time_labels.append(t_str)

            # -- Partie Soil Moisture : on ajoute la valeur dans le bon "sensor_location"
            loc_id = data.sensor_location_id
            soil_moisture_value = data.soil_moisture if data.soil_moisture is not None else None
            soil_moisture_dict[loc_id]['timestamps'].append(t_str)
            soil_moisture_dict[loc_id]['values'].append(soil_moisture_value)

        # On récupère le dernier point
        latest_data = sensor_data.last()
        current_temperature = latest_data.temperature if latest_data.temperature is not None else 0
        current_humidity = latest_data.air_humidity if latest_data.air_humidity is not None else 0
        if hasattr(latest_data, 'water_level') and latest_data.water_level is not None:
            current_water_level = latest_data.water_level

    # =============================
    # Construit les traces d’humidité du sol
    # =============================
    soil_moisture_traces = []
    for loc_id, info in soil_moisture_dict.items():
        # S’il n’y a pas de timestamps (pas de data), on ignore
        if not info['timestamps']:
            continue
        # Chaque location = une courbe (trace) sur le même graphique
        soil_moisture_traces.append({
            'x': info['timestamps'],
            'y': info['values'],
            'mode': 'lines+markers',
            'type': 'scatter',
            'name': info['name']  # Nom d'emplacement/capteur
        })

    # =============================
    # Calcule la moyenne pour la jauge
    # =============================
    # On parcourt toutes les locations, on prend la DERNIÈRE valeur si disponible
    sum_soil = 0
    count_soil = 0
    for loc_id, info in soil_moisture_dict.items():
        if info['values']:
            last_val = info['values'][-1]
            if last_val is not None:
                sum_soil += last_val
                count_soil += 1

    if count_soil > 0:
        current_soil_moisture = sum_soil / count_soil
    else:
        current_soil_moisture = 0

    # =============================
    # GESTION DU TITRE & AXE X
    # =============================
    if sensor_data.exists() and len(time_labels) > 1:
        x_range = [time_labels[0], time_labels[-1]]
        auto_x = False
    else:
        x_range = []
        auto_x = True

    # Titres des graphiques
    titre_temperature = "Température (°C)" if temperature_data else "Aucune donnée disponible"
    titre_humidite = "Humidité (%)" if humidity_data else "Aucune donnée disponible"
    # On vérifie si on a au moins une trace d’humidité du sol
    titre_sol = "Évolution de l’humidité du sol" if soil_moisture_traces else "Aucune donnée disponible"
    titre_niveau_eau = "Niveau d’eau (%)" if water_level_data else "Aucune donnée disponible"

    # =============================
    # Prépare les « gauges » (jauges)
    # =============================
    gauges = [
        {
            'id': 'temperatureGauge',
            'title': 'Température actuelle',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_temperature,
                    'gauge': {
                        'axis': {'range': [0, 50]},
                        'bar': {'color': 'blue'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Température (°C)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'humidityGauge',
            'title': 'Humidité actuelle',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_humidity,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': 'green'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Humidité (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'soilMoistureGauge',
            'title': 'Humidité du sol',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    # ICI => la moyenne de tous les capteurs
                    'value': current_soil_moisture,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': '#8B4513'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Humidité du sol (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
        {
            'id': 'waterLevelGauge',
            'title': 'Niveau d’eau',
            'json': json.dumps({
                'data': [{
                    'type': 'indicator',
                    'mode': 'gauge+number',
                    'value': current_water_level,
                    'gauge': {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': 'blue'},
                        'borderwidth': 2,
                        'bordercolor': '#888'
                    }
                }],
                'layout': {
                    'title': 'Niveau d’eau (%)',
                    'paper_bgcolor': 'white',
                    'plot_bgcolor': 'white',
                    'font': {'color': '#333'}
                }
            })
        },
    ]

    # =============================
    # Prépare les « charts » (diagrammes linéaires)
    # =============================

    # Chart de la température
    charts = [
        {
            'id': 'temperatureChart',
            'title': 'Évolution de la température',
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': temperature_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'red'},
                    'marker': {'color': 'red'}
                }],
                'layout': {
                    'title': titre_temperature,
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': auto_x
                    },
                    'yaxis': {
                        'title': '°C',
                        'range': [-10, 50],
                        'autorange': False
                    }
                }
            })
        },
        {
            'id': 'humidityChart',
            'title': "Évolution de l'humidité de l’air",
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': humidity_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'blue'},
                    'marker': {'color': 'blue'}
                }],
                'layout': {
                    'title': titre_humidite,
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': auto_x
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
                }
            })
        },
        {
            'id': 'soilMoistureChart',
            'title': 'Évolution de l’humidité du sol',
            'json': json.dumps({
                # ICI => on fournit la liste de "traces" pour chaque location
                'data': soil_moisture_traces,
                'layout': {
                    'title': titre_sol,
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': auto_x
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
                }
            })
        },
        {
            'id': 'waterLevelChart',
            'title': "Évolution du niveau d’eau",
            'json': json.dumps({
                'data': [{
                    'x': time_labels,
                    'y': water_level_data,
                    'mode': 'lines+markers',
                    'type': 'scatter',
                    'line': {'color': 'dodgerblue'},
                    'marker': {'color': 'dodgerblue'}
                }],
                'layout': {
                    'title': titre_niveau_eau,
                    'paper_bgcolor': '#f9f9f9',
                    'plot_bgcolor': '#f9f9f9',
                    'font': {'color': '#333'},
                    'xaxis': {
                        'title': 'Temps',
                        'range': x_range,
                        'autorange': auto_x
                    },
                    'yaxis': {
                        'title': '%',
                        'range': [0, 100],
                        'autorange': False
                    }
                }
            })
        },
    ]

    return render(request, 'graph.html', {
        'raspberry': raspberry,
        'gauges': gauges,
        'charts': charts,
        'selected_time_range': selected_time_range
    })

@login_required(login_url='login')
def raspberry_update(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)

    if request.method == 'POST':
        form = RaspberryForm(request.POST, instance=raspberry)
        if form.is_valid():
            form.save()
            return redirect('home')
    else:
        form = RaspberryForm(instance=raspberry)

    return render(request, 'raspberry_form.html', {
        'form': form,
        'raspberry': raspberry,
        'action': 'Modifier'
    })

@login_required(login_url='login')
def raspberry_delete(request, id):
    raspberry = get_object_or_404(Raspberry, id=id)
    raspberry.delete()
    return redirect('home')

@login_required(login_url='login')
def toggle_device(request, id, device):
    raspberry = get_object_or_404(Raspberry, id=id)
    if request.method == 'POST':
        if device == 'pump':
            raspberry.pump_state = not raspberry.pump_state
            messages.success(request, "L'état de la pompe a été modifié.")
        elif device == 'fan':
            raspberry.fan_state = not raspberry.fan_state
            messages.success(request, "L'état du ventilateur a été modifié.")
        else:
            messages.error(request, "Appareil inconnu.")
        raspberry.save()
    else:
        messages.error(request, "Méthode non autorisée.")
    # Rediriger vers la page de gestion de la serre
    return redirect('manage_greenhouse', id=raspberry.id)

