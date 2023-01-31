# hsdb_spd

Heritage Science DB Spectral Data Processor

```bash
  pip install pipenv
  pipenv shell --python 3.8
  pipenv install
  pipenv install -d
```

```bash
  cp .sample.env .env
```

```bash
  export PYTHONPATH=$PWD
```

Run celery and fast-api with honcho (see `Procfile`)
```bash
  honcho start
```

[Async Architecture with FastAPI, Celery, and RabbitMQ | by Suman Das | Crux Intelligence | Medium][1]

[1]: https://medium.com/cuddle-ai/async-architecture-with-fastapi-celery-and-rabbitmq-c7d02903037
