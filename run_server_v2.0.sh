#!/bin/bash

# Este script define el entorno virtual y ejecuta el servidor

VENV_DIR=".venv_server"

echo "=== Configurando el entorno para el Servidor ==="

# Si no existe la carpeta, crear el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activar el entorno
source "$VENV_DIR/bin/activate"

# Instalar/actualizar requerimientos
echo "Instalando y actualizando dependencias de VENV a lo mas nuevo..."
python3 -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt --upgrade --upgrade-strategy eager

# Correr el servidor
echo "Arrancando el servidor..."
python3 server.v.2.0.py

# Desactivar el entorno al salir
deactivate
