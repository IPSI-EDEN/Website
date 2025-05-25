# Eden project - Site web

## Présentation

Cette partie du projet est une application web Django permettant la gestion de serres connectées, le suivi de capteurs, la gestion des groupes d'utilisateurs et l'administration de dispositifs Raspberry Pi.

---

## Structure des paramètres (`settings`)

Le dossier [`Eden/settings`](Eden/settings) contient la configuration Django organisée par environnement :

- **`base.py`** : configuration commune à tous les environnements (apps, middleware, base de données par défaut, etc.).
- **`local.py`** : configuration pour le développement local (utilise SQLite, DEBUG=True, etc.).
- **`production.py`** : configuration pour la production (PostgreSQL, sécurité renforcée, logs, etc.).
- **`test.py`** : configuration pour les tests (base en mémoire, etc.).
- **`__init__.py`** : sélectionne automatiquement le bon fichier de configuration selon la variable d'environnement `DJANGO_ENV` (`local`, `production`, `test`).

**Exemple :**
Pour lancer le projet en production, définissez la variable d'environnement :
```sh
export DJANGO_ENV=production
```

---

## Utilisation du script `manage.py`

Le script [`manage.py`](manage.py) est le point d'entrée pour toutes les commandes d'administration Django :

- **Lancer le serveur de développement :**
  ```sh
  python manage.py runserver
  ```
- **Appliquer les migrations (modifications de la base de données) :**
  ```sh
  python manage.py migrate
  ```
- **Créer un superutilisateur :**
  ```sh
  python manage.py createsuperuser
  ```

Le script utilise la variable d'environnement `DJANGO_SETTINGS_MODULE` qui est automatiquement gérée par le système de sélection dans [`Eden/settings/__init__.py`](Eden/settings/__init__.py).

---

## Workflow général

1. **Configuration des variables d'environnement :**
   - Placez vos secrets dans le fichier [.env](.env) à la racine du projet (créez-le si nécessaire) :
     ```
     AES_SECRET_KEY='...'
     DJANGO_SECRET_KEY='...'
     ```
2. **Choix de l'environnement :**
   - Définissez `DJANGO_ENV` à `local`, `production` ou `test` selon le contexte.
3. **Installation des dépendances :**
    - Installez les dépendances Python avec :
    ```sh
    pip install -r requirements.txt
    ```
4. **Création du fichier de base de données (pour l'environnement local) :**
    - Si vous utilisez SQLite (par défaut en local), le fichier `db.sqlite3` sera créé automatiquement lors de la première migration :
    ```sh
    python manage.py migrate
    ```
    - Si vous souhaitez utiliser un fichier spécifique ou le versionner, créez-le manuellement ou copiez un fichier existant à la racine du projet.
5. **Migrations et lancement :**
   ```sh
   python manage.py migrate
   python manage.py runserver
   ```
6. **Déploiement :**
   - Utilisez le fichier [`Dockerfile`](Dockerfile) et [`docker-compose.yml`](docker-compose.yml) pour déployer en production.
   - Les logs sont stockés dans `/app/logs` en production.

---

## Conseil pour le développement d'une nouvelle fonctionnalité

Avant de commencer, créez une nouvelle branche Git. Ajoutez vos modèles (si nécessaire, pour la base de données) dans [`Website/models.py`](Website/models.py), créez une vue dans [`Website/views`](Website/views/) (en html), puis ajoutez vos routes dans [`Eden/urls.py`](Eden/urls.py), ajustez si besoin les styles CSS dans [`Eden/static`](Eden/static/). N'oubliez pas d'écrire des tests dans [`Website/tests.py`](Website/tests.py) et de lancer :

```sh
python manage.py makemigrations
python manage.py migrate
```

Vérifiez vos modifications en lançant le serveur de développement :

```sh
python manage.py runserver
```

et en accédant à l'URL correspondante dans votre navigateur.


**Astuce :** Pour que vos signaux Django soient bien pris en compte, ajoutez leur import dans la méthode `ready()` de [`Website/apps.py`](Website/apps.py).

---