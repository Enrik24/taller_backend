#!/usr/bin/env bash

set -e

export DISABLE_POETRY=1

pip install --no-cache-dir -r requirements.txt

python -c "
import sys
from pathlib import Path
sys.path.append(str(Path('.').resolve()))
from app.database import engine, Base
from app.modules.usuarios.models import *
from app.modules.solicitudes.models import *
from app.modules.pagos.models import *
from app.modules.notificaciones.models import *
from app.modules.talleres.models import *
Base.metadata.create_all(bind=engine)
print('✅ Tablas creadas')
"

python seed.py
