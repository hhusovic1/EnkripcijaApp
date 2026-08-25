"""
Razvojni server za Flask aplikaciju.

    python server.py

U produkciji se koristi WSGI server, ne ovaj:
    gunicorn wsgi:app
"""
from web import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="localhost", port=5000, debug=True)
