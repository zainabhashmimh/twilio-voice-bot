#web: gunicorn app:app
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT

