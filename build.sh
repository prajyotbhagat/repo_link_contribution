#!/bin/bash

python manage.py migrate --noinput
python manage.py loaddata initial_data.json