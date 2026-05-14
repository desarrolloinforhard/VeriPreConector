import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from core.logging.logger import get_logger


logger = get_logger(__name__)

CONFIG_FILENAME = "config.json"
APP_DIRNAME = "SmartPrice"
ENV_CONFIG_DIR = "SMARTPRICE_CONFIG_DIR"


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _legacy_candidates() -> list[Path]:
    candidates = []
    project_root = _project_root()
    cwd_path = Path.cwd() / CONFIG_FILENAME
    project_config = project_root / CONFIG_FILENAME

    for path in (cwd_path, project_config):
        if path not in candidates:
            candidates.append(path)

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        for path in (
            exe_dir / "_internal" / CONFIG_FILENAME,
            exe_dir / CONFIG_FILENAME,
        ):
            if path not in candidates:
                candidates.append(path)

    return candidates


def _default_config_dir() -> Path:
    if os.getenv(ENV_CONFIG_DIR):
        return Path(os.getenv(ENV_CONFIG_DIR)).expanduser()

    if getattr(sys, "frozen", False):
        program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData"))
        return program_data / APP_DIRNAME

    return _project_root()


def obtener_data_dir() -> Path:
    data_dir = _default_config_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def obtener_config_path() -> Path:
    config_dir = obtener_data_dir()
    config_path = config_dir / CONFIG_FILENAME

    if not config_path.exists():
        for legacy_path in _legacy_candidates():
            if legacy_path.exists():
                try:
                    shutil.copy2(legacy_path, config_path)
                    logger.info(
                        "Config migrado a ruta persistente | origen=%s | destino=%s",
                        legacy_path,
                        config_path,
                    )
                    break
                except OSError:
                    logger.exception(
                        "No se pudo migrar config legado | origen=%s | destino=%s",
                        legacy_path,
                        config_path,
                    )

    return config_path


def cargar_config():
    config_path = obtener_config_path()
    if not config_path.exists():
        logger.info("Config no existe todavia. Se devolvera diccionario vacio | path=%s", config_path)
        return {}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError:
        logger.exception("Config JSON invalido | path=%s", config_path)
        return {}
    except OSError:
        logger.exception("No se pudo leer config.json | path=%s", config_path)
        return {}


def guardar_config(data):
    config_path = obtener_config_path()
    temp_fd = None
    temp_path = None

    try:
        temp_fd, temp_path = tempfile.mkstemp(
            prefix="config_",
            suffix=".tmp",
            dir=str(config_path.parent),
        )
        with os.fdopen(temp_fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        temp_fd = None
        os.replace(temp_path, config_path)
        logger.debug("Config guardado correctamente | path=%s", config_path)
    except OSError:
        logger.exception("No se pudo guardar config.json | path=%s", config_path)
        raise
    finally:
        if temp_fd is not None:
            try:
                os.close(temp_fd)
            except OSError:
                pass
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
