# Déploiement du Projet sur Heroku depuis GitHub

Ce guide décrit les étapes pour déployer ce projet Django sur Heroku en utilisant GitHub pour le versionnement du code.

## Étape 1 : Préparation du Projet pour le Déploiement

Avant de déployer, nous devons configurer le projet pour un environnement de production.

### 1.1. Gérer les Fichiers Statiques avec WhiteNoise

WhiteNoise permet à notre application de servir ses propres fichiers statiques en production.

Modifiez `eventify/settings.py` pour ajouter le middleware WhiteNoise. Il doit se trouver juste après le `SecurityMiddleware`.

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # <-- Ajoutez cette ligne
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```

### 1.2. Créer un `Procfile`

Heroku a besoin d'un `Procfile` pour savoir quelle commande lancer pour démarrer l'application. Créez un fichier nommé `Procfile` (sans extension) à la racine du projet avec le contenu suivant :

```
web: gunicorn eventify.wsgi --log-file -
```
Cette ligne indique à Heroku de démarrer un serveur web `gunicorn` en utilisant la configuration WSGI de notre projet.

## Étape 2 : Mettre le Projet sur GitHub

### 2.1. Créer un `.gitignore`

Il est crucial de ne pas inclure de fichiers sensibles ou inutiles dans le dépôt Git. Créez un fichier `.gitignore` à la racine du projet.

```
# Fichiers de cache Python
__pycache__/
*.pyc

# Fichiers de l'éditeur
.vscode/
.idea/

# Fichiers de base de données
*.sqlite3
db.sqlite3

# Fichiers d'environnement
.env

# Fichiers média
/media/

# Fichiers statiques collectés
/static/

# Fichiers du virtualenv
event/
```

### 2.2. Initialiser Git et Pousser sur GitHub

1.  **Initialisez un dépôt Git local :**
    ```bash
    git init
    ```
2.  **Ajoutez tous les fichiers au suivi :**
    ```bash
    git add .
    ```
3.  **Faites votre premier commit :**
    ```bash
    git commit -m "Initial commit"
    ```
4.  **Créez un nouveau dépôt sur GitHub.**
5.  **Liez votre dépôt local au dépôt distant sur GitHub :**
    ```bash
    git remote add origin https://github.com/VOTRE_NOM_UTILISATEUR/NOM_DE_VOTRE_DEPOT.git
    ```
6.  **Poussez votre code sur GitHub :**
    ```bash
    git push -u origin master
    ```

## Étape 3 : Déployer sur Heroku

### 3.1. Créer une Application Heroku

1.  **Installez le [Heroku CLI](https://devcenter.heroku.com/articles/heroku-cli).**
2.  **Connectez-vous à votre compte Heroku :**
    ```bash
    heroku login
    ```
3.  **Créez une nouvelle application Heroku :**
    ```bash
    heroku create nom-de-votre-app
    ```
    Si vous ne spécifiez pas de nom, Heroku en générera un pour vous.

### 3.2. Configurer les Variables d'Environnement

Nous devons configurer les variables d'environnement sur Heroku pour les paramètres sensibles.

1.  **`SECRET_KEY` :**
    Récupérez votre `SECRET_KEY` dans `eventify/settings.py` et configurez-la sur Heroku :
    ```bash
    heroku config:set SECRET_KEY='votre_secret_key_ici'
    ```
2.  **`ALLOWED_HOSTS` :**
    Nous devons autoriser le domaine de notre application Heroku. Modifiez `eventify/settings.py` pour lire les `ALLOWED_HOSTS` depuis les variables d'environnement.

    ```python
    # eventify/settings.py
    import environ
    env = environ.Env()

    # ...

    ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.herokuapp.com', '127.0.0.1'])
    ```

### 3.3. Déployer

Connectez votre dépôt GitHub à Heroku pour un déploiement automatique.

1.  **Allez sur le tableau de bord de votre application Heroku.**
2.  **Allez dans l'onglet "Deploy".**
3.  **Dans la section "Deployment method", choisissez "GitHub".**
4.  **Connectez votre compte GitHub et recherchez votre dépôt.**
5.  **Activez les déploiements automatiques** pour la branche `master` (ou `main`).
6.  **Déclenchez un déploiement manuel** pour la première fois.

### 3.4. Lancer les Migrations

Après le déploiement, vous devez appliquer les migrations de la base de données sur Heroku.

```bash
heroku run python manage.py migrate
```

### 3.5. Créer un Superutilisateur (Optionnel)

Si vous avez besoin d'accéder à l'interface d'administration de Django, créez un superutilisateur.

```bash
heroku run python manage.py createsuperuser
```

Votre application est maintenant déployée ! Vous pouvez l'ouvrir en utilisant la commande `heroku open`.
