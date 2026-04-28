#!/usr/bin/env bash

set -e

pip install --no-cache-dir -r requirements.txt

alembic upgrade head

python seed.py
