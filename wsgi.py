"""WSGI ulazna tacka za produkciju (gunicorn wsgi:app)."""
from web import create_app

app = create_app()
