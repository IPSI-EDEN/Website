from .home import *

@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def receive_sensor_data(request):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting receive_sensor_data. Method={request.method}")

    try:
        encrypted_data_b64 = request.data.get('encrypted')
        logger.info(f"[{request_id}] Received encrypted data payload.")

        if not encrypted_data_b64:
            logger.warning(f"[{request_id}] Missing encrypted data in request.")
            return Response({"error": "Données chiffrées manquantes."}, status=status.HTTP_400_BAD_REQUEST)

        # Décryptage des données
        encrypted_data = base64.b64decode(encrypted_data_b64)
        nonce = encrypted_data[:12]
        ciphertext = encrypted_data[12:]

        aesgcm = AESGCM(settings.AES_SECRET_KEY)
        decrypted_data = aesgcm.decrypt(nonce, ciphertext, None)
        data = json.loads(decrypted_data.decode('utf-8'))
        logger.debug(f"[{request_id}] Decrypted data: {data}")

        # Validation des données
        serializer = IncomingDataSerializer(data=data)
        if not serializer.is_valid():
            logger.error(f"[{request_id}] Validation errors: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data

        timestamp = validated_data['timestamp']
        raspberry_data = validated_data['raspberry']
        device_name = raspberry_data.get('device_name')
        locations = validated_data['locations']
        temperature = validated_data['temperature']
        air_humidity = validated_data['air_humidity']

        with transaction.atomic():
            # Récupérer ou créer le groupe par défaut
            group, _ = Group.objects.get_or_create(
                name=DEFAULT_GROUP_NAME,
                defaults={'description': "Default group for unassigned Raspberries."}
            )

            # Récupérer ou créer le Raspberry
            raspberry, created_raspberry = Raspberry.objects.get_or_create(
                device_id=device_name,
                defaults={
                    'group': group,
                    'active': True,
                    'status': 'unassigned'
                }
            )
            if created_raspberry:
                logger.info(f"[{request_id}] Created new Raspberry device_id={raspberry.device_id}")

            # Pour chaque emplacement, récupérer/créer le Plant et le SensorLocation, puis enregistrer les données
            for loc in locations:
                location_name = loc['location_name']
                loc_soil_moisture = loc['soil_moisture']

                plant, _ = Plant.objects.get_or_create(
                    name=location_name,
                    defaults={
                        'description': f'Plant for {location_name}',
                        'temperature_min': 10.0,
                        'temperature_max': 35.0,
                        'humidity_min': 30.0,
                        'humidity_max': 80.0,
                        'soil_moisture_min': 20.0,
                        'soil_moisture_max': 70.0,
                    }
                )

                sensor_location, _ = SensorLocation.objects.get_or_create(
                    raspberry=raspberry,
                    location_name=location_name,
                    defaults={'plant': plant}
                )
                sensor_location.soil_moisture = loc_soil_moisture
                sensor_location.save()

                SensorData.objects.create(
                    sensor_location=sensor_location,
                    timestamp=timestamp,
                    temperature=temperature,
                    air_humidity=air_humidity,
                    soil_moisture=loc_soil_moisture
                )

        logger.info(f"[{request_id}] Sensor data saved successfully.")
        raspberry_data = {
            'id': raspberry.id,
            'device_id': raspberry.device_id,
            'group': raspberry.group.name if raspberry.group else "Non Assigné",
            'active': raspberry.active,
            'pump': raspberry.pump_state,
            'fan': raspberry.fan_state,
        }

        success_message = {
            "message": "Données enregistrées avec succès.",
            "raspberry": raspberry_data
        }

        nonce = os.urandom(12)
        data_bytes = json.dumps(success_message).encode('utf-8')
        ciphertext = aesgcm.encrypt(nonce, data_bytes, None)
        encrypted_data = nonce + ciphertext
        encrypted_data_b64 = base64.b64encode(encrypted_data).decode('utf-8')

        logger.debug(f"[{request_id}] Sending encrypted response back.")
        return Response({"encrypted": encrypted_data_b64}, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.exception(f"[{request_id}] Error processing sensor data: {e}")
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_latest_sensor_data(request, raspberry_id):
    request_id = str(uuid.uuid4())
    logger.debug(f"[{request_id}] Starting get_latest_sensor_data. User={request.user}, RaspberryID={raspberry_id}")

    try:
        raspberry = get_object_or_404(Raspberry, id=raspberry_id)
        logger.info(f"[{request_id}] Accessing data for Raspberry {raspberry_id}, User={request.user}")

        if not request.user.is_superuser and not request.user.is_staff:
            user_groups = Group.objects.filter(
                raspberries=raspberry,
                user_groups__user=request.user
            )
            if not user_groups.exists():
                logger.warning(f"[{request_id}] User {request.user} does not have access to Raspberry {raspberry_id}.")
                return Response({"error": "Accès non autorisé."}, status=status.HTTP_403_FORBIDDEN)

        time_range = request.GET.get('time_range', '24')
        logger.debug(f"[{request_id}] time_range={time_range}")

        try:
            time_range = int(time_range)
        except ValueError:
            logger.error(f"[{request_id}] Invalid time_range: {time_range}")
            return Response({"error": "Valeur de time_range invalide."}, status=status.HTTP_400_BAD_REQUEST)

        end_time = now()
        start_time = end_time - timedelta(hours=time_range)

        sensor_locations = SensorLocation.objects.filter(raspberry=raspberry)
        sensor_data = SensorData.objects.filter(
            sensor_location__in=sensor_locations,
            timestamp__gte=start_time
        ).order_by('timestamp')

        serializer = SensorDataSerializer(sensor_data, many=True)
        logger.info(f"[{request_id}] Returning {sensor_data.count()} records of SensorData for Raspberry {raspberry_id} to User={request.user}.")
        return Response(serializer.data, status=status.HTTP_200_OK)

    except Exception as e:
        logger.exception(f"[{request_id}] Error in get_latest_sensor_data for Raspberry={raspberry_id}: {e}")
        return Response({"error": "Erreur interne du serveur."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)