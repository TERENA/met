#!/bin/bash

NAME="met"                                        # name of the application
DJANGODIR=/opt/met                                # Django project directory
SOCKDIR=/run/met                                  # path where to create sock file
SOCKFILE=$SOCKDIR/gunicorn.sock                   # we will communicte using this unix socket
USER=www-data                                     # the user to run as
GROUP=www-data                                    # the group to run as
NUM_WORKERS=3                                     # how many worker processes should Gunicorn spawn
DJANGO_SETTINGS_MODULE=met.settings               # which settings file should Django use
DJANGO_WSGI_MODULE=met.wsgi                       # WSGI module name
TIMEOUT=900

export PYTHON_EGG_CACHE=/tmp/.python-eggs

VENV=../met-venv
#VENV=../met-venv-pypy

if [ ! -d "$SOCKDIR" ]; then
	mkdir $SOCKDIR
	chown $USER.$GROUP $SOCKDIR
fi

echo "Starting $NAME as `whoami`"

# Activate the virtual environment
cd $DJANGODIR
source $VENV/bin/activate
export DJANGO_SETTINGS_MODULE=$DJANGO_SETTINGS_MODULE
export PYTHONPATH=$DJANGODIR:$PYTHONPATH

# Create the run directory if it doesn't exist
RUNDIR=$(dirname $SOCKFILE)
test -d $RUNDIR || mkdir -p $RUNDIR

# Start your Django Unicorn
# Programs meant to be run under supervisor should not daemonize themselves (do not use --daemon)
exec $VENV/bin/gunicorn ${DJANGO_WSGI_MODULE}:application \
  --name $NAME \
  --workers $NUM_WORKERS \
  --user=$USER --group=$GROUP \
  --bind=unix:$SOCKFILE \
  --timeout $TIMEOUT \
  --log-level=error \
  --log-file=- \
  --max-requests 100
