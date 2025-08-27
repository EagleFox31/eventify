#!/usr/bin/env bash
# Script de build pour Render

# Installer les dépendances
pip install -r requirements.txt

# Lancer les migrations
python manage.py migrate --noinput

# Collecter les fichiers statiques
python manage.py collectstatic --noinput
