#!/bin/bash

# A handy wrapper around docker to run a postgres container

# DATABASE_URL=postgres://user:password@localhost:5432/postgres

migrate() {
    python manage.py migrate
}

createsuperuser() {
    # See https://docs.djangoproject.com/en/3.0/ref/django-admin/#createsuperuser
    # You'll want DJANGO_SUPERUSER_PASSWORD to be set.
    python manage.py createsuperuser --username dev@frontseat.org --email dev@frontseat.org --noinput
}

up() {
    docker run --name pg-engage -p 5432:5432 -e POSTGRES_PASSWORD=password -e POSTGRES_USER=user -d postgres:15
    sleep 5
    migrate
    createsuperuser
}

down() {
    docker stop pg-engage
    docker rm pg-engage
}

restart() {
    stop
    start
}

resetdb() {
    PGPASSWORD=password dropdb --host=localhost --port=5432 --username=user --no-password postgres
    PGPASSWORD=password createdb --host=localhost --port=5432 --username=user --no-password postgres
    migrate
    createsuperuser
}

logs() {
    docker logs pg-engage
}

status() {
    docker ps | grep pg-engage
}


case "$1" in
     'up')
        up
        ;;
    'down')
        down
        ;;
    'restart')
        restart
        ;;
    'resetdb')
        resetdb
        ;;
    'logs')
        logs
        ;;
    'status')
        status
        ;;
    'migrate')
        migrate
        ;;
    *)
        echo
        echo "Usage: $0 { up | down | restart | resetdb | logs | status | migrate }"
        echo
        exit 1
esac

exit 0

