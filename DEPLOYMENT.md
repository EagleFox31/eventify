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

## Étape 4 : Déployer sur Render (Alternative)

Render est une alternative moderne à Heroku. Le processus est similaire et se base également sur votre dépôt GitHub.

### 4.1. Pré-requis

- Assurez-vous que votre projet est sur GitHub (voir Étape 2).
- Les dépendances de production (`gunicorn`, `whitenoise`, `django-environ`) doivent être dans `requirements.txt`.
- Votre projet doit être configuré pour lire les variables d'environnement (comme `SECRET_KEY` et `ALLOWED_HOSTS`).

### 4.2. Créer un "Web Service" sur Render

1.  **Créez un compte sur [Render](https://render.com/).**
2.  **Allez sur votre Dashboard et cliquez sur "New" > "Web Service".**
3.  **Connectez votre compte GitHub** et sélectionnez le dépôt de votre projet.
4.  **Configurez le service :**
    - **Name:** Donnez un nom à votre service (ex: `eventify-app`).
    - **Region:** Choisissez une région proche de vos utilisateurs.
    - **Branch:** Sélectionnez la branche à déployer (`master` ou `main`).
    - **Build Command:** `pip install -r requirements.txt`
    - **Start Command:** `gunicorn eventify.wsgi`
    - **Instance Type:** "Free" est suffisant pour commencer.

### 4.3. Configurer les Variables d'Environnement

Dans la section "Environment", ajoutez les variables suivantes :

- **`SECRET_KEY`**: Copiez-collez votre clé secrète.
- **`PYTHON_VERSION`**: Spécifiez la version de Python que vous utilisez (ex: `3.12.0`).
- **`ALLOWED_HOSTS`**: Vous n'avez pas besoin de configurer `ALLOWED_HOSTS` manuellement. Render injecte automatiquement le domaine de votre application (`.onrender.com`) dans les variables d'environnement. Il suffit de modifier `settings.py` pour l'accepter.

```python
# eventify/settings.py

# ...

# Pour Render, ajoutez '.onrender.com' à la liste des domaines autorisés par défaut.
# La configuration finale devrait ressembler à ceci pour supporter les deux plateformes :
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['.herokuapp.com', '.onrender.com', '127.0.0.1'])
```
*Note : Si vous avez déjà configuré `ALLOWED_HOSTS` pour Heroku, il suffit d'y ajouter le domaine de Render.*

### 4.4. Configurer la Base de Données (Optionnel mais Recommandé)

Le plan gratuit de Render ne conserve pas les données stockées sur le disque (comme `db.sqlite3`) entre les déploiements. Il est fortement recommandé d'utiliser une base de données managée comme PostgreSQL.

1.  **Sur Render, créez un service "PostgreSQL".**
2.  Une fois la base de données créée, Render vous fournira une **"Database URL"**.
3.  Ajoutez une nouvelle variable d'environnement à votre "Web Service" :
    - **Key:** `DATABASE_URL`
    - **Value:** Collez l'URL fournie par Render.
4.  Installez `dj-database-url` pour que Django puisse lire cette URL :
    - Ajoutez `dj-database-url` à votre `requirements.txt`.
    - Modifiez `settings.py` pour utiliser cette variable :

    ```python
    # eventify/settings.py
    import dj_database_url

    # ...

    DATABASES = {
        'default': env.db('DATABASE_URL', default='sqlite:///db.sqlite3')
    }
    ```

### 4.5. Déployer

Cliquez sur **"Create Web Service"**. Render va maintenant construire et déployer votre application. Les déploiements futurs seront automatiques à chaque `push` sur la branche configurée.

Une fois le déploiement terminé, n'oubliez pas d'exécuter les migrations via la console de Render :

```bash
python manage.py migrate
```

Votre application est maintenant en ligne sur Render !
