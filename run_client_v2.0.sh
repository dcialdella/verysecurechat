#!/bin/bash

# Este script define el entorno virtual y ejecuta el cliente

VENV_DIR=".venv_client"

echo "=== Configurando el entorno para el Cliente ==="

# Si no existe la carpeta, crear el entorno virtual
if [ ! -d "$VENV_DIR" ]; then
    echo "Creando entorno virtual en $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

# Activar el entorno
source "$VENV_DIR/bin/activate"

# Instalar/actualizar requerimientos
echo "Instalando dependencias necesarias (python-gnupg)..."
pip install --upgrade pip
pip install -r requirements.txt --upgrade

# Correr el cliente
echo "Arrancando el cliente Tkinter..."
python3 client.v.2.0.py

# Desactivar el entorno al salir
deactivate
