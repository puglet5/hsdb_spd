# hsdb_spd

Heritage Science DB Spectral Data Processor

```bash
  pip install pipenv
  pipenv shell --python 3.10.6
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


[How To Install and Start Using RabbitMQ on Ubuntu 22.04][2]


[1]: https://medium.com/cuddle-ai/async-architecture-with-fastapi-celery-and-rabbitmq-c7d02903037
[2]: https://www.cherryservers.com/blog/how-to-install-and-start-using-rabbitmq-on-ubuntu-22-04
