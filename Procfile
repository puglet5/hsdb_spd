uvicorn: python app/main.py
celery: celery -A app.main.celery worker --loglevel=info -Q spectra
flower: celery -A app.main.celery flower --port=5555
