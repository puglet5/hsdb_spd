uvicorn: python app/main.py
celery: watchmedo auto-restart -R -d ./app/ -p '*.py' -- celery -A app.main.celery worker -Q spectra --concurrency 10 -P threads --without-gossip --loglevel=info
flower: celery -A app.main.celery flower --port=5555
