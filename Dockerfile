# Utiliser l'image officielle de Python comme base
FROM python:3.11-slim

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le fichier requirements.txt dans le conteneur
COPY requirements.txt .

# Créer un environnement virtuel
RUN python -m venv .env

# Activer l'environnement virtuel et installer les dépendances
RUN sudo .env/bin/activate && pip install --no-cache-dir -r requirements.txt

# Copier tout le code de votre application Django dans le conteneur
COPY . .

# Exposer le port sur lequel Django fonctionne (par défaut 8000)
EXPOSE 8000

# Commande par défaut pour lancer l'application Django
CMD ["sh", "-c", "sudo .env/bin/activate && python manage.py runserver 0.0.0.0:8000"]