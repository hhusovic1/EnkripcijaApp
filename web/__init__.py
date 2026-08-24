"""
Flask aplikacija - web sloj iznad core/, attacks/ i benchmark/.

Sav kriptografski kod je UI-agnostican: ovaj paket ga samo izlaze kroz HTTP,
ne implementira nista svoje.

Pokretanje u razvoju:
    python server.py

U produkciji (WSGI):
    gunicorn wsgi:app
"""
from flask import Flask


def create_app(config=None) -> Flask:
    app = Flask(__name__)
    app.config.update(
        JSON_AS_ASCII=False,
        # Ogranicenje velicine zahtjeva - rucne implementacije ionako obradjuju
        # najvise nekoliko desetina kilobajta u interaktivnom radu.
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
    )
    if config:
        app.config.update(config)

    from .api import api
    from .routes import glavni

    app.register_blueprint(glavni)
    app.register_blueprint(api)

    return app
