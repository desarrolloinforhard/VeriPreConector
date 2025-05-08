import os
import json

CONFIG_PATH = os.path.join("config.json")  # Ajustá según tu estructura

def cargar_config():
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {}

def guardar_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=4)
