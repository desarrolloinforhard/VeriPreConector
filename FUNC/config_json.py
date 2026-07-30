import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path

from core.logging.logger import get_logger


logger = get_logger(__name__)

CONFIG_FILENAME = "config.json"
DB_FILENAME = "veripre.db"
APP_DIRNAME = "SmartPrice"
ENV_CONFIG_DIR = "SMARTPRICE_CONFIG_DIR"
CONFIG_LOCK_FILENAME = "config.lock"
CONFIG_LOCK_TIMEOUT_SECONDS = 12
CONFIG_LOCK_RETRY_SECONDS = 0.2
CONFIG_REPLACE_RETRIES = 20
CONFIG_REPLACE_RETRY_SECONDS = 0.15


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


def _legacy_db_candidates() -> list[Path]:
    project_root = _project_root()
    candidates = [
        project_root / "DB" / DB_FILENAME,
        project_root / "db" / DB_FILENAME,
        Path.cwd() / "DB" / DB_FILENAME,
        Path.cwd() / "db" / DB_FILENAME,
        Path.cwd() / DB_FILENAME,
    ]

    if getattr(sys, "frozen", False):
        exe_dir = Path(sys.executable).resolve().parent
        candidates.extend(
            [
                exe_dir / "_internal" / "DB" / DB_FILENAME,
                exe_dir / "_internal" / "db" / DB_FILENAME,
                exe_dir / "DB" / DB_FILENAME,
                exe_dir / "db" / DB_FILENAME,
                exe_dir / DB_FILENAME,
            ]
        )

    unique = []
    seen = set()
    for path in candidates:
        key = str(path).lower()
        if key not in seen:
            seen.add(key)
            unique.append(path)
    return unique


def obtener_sqlite_path() -> Path:
    if not getattr(sys, "frozen", False):
        return _project_root() / "DB" / DB_FILENAME

    data_dir = obtener_data_dir()
    db_path = data_dir / DB_FILENAME
    fallback_path = None

    if not db_path.exists():
        for legacy_path in _legacy_db_candidates():
            if not legacy_path.exists():
                continue
            if fallback_path is None:
                fallback_path = legacy_path
            try:
                db_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy_path, db_path)
                logger.info(
                    "SQLite migrado a ruta persistente | origen=%s | destino=%s",
                    legacy_path,
                    db_path,
                )
                break
            except OSError:
                logger.exception(
                    "No se pudo migrar SQLite legado | origen=%s | destino=%s",
                    legacy_path,
                    db_path,
                )

    if db_path.exists():
        return db_path

    if fallback_path is not None:
        logger.warning(
            "Usando SQLite legado por no poder migrarlo a la ruta persistente | path=%s",
            fallback_path,
        )
        return fallback_path

    return db_path


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


def _acquire_config_lock(config_dir: Path):
    lock_path = config_dir / CONFIG_LOCK_FILENAME
    deadline = time.time() + CONFIG_LOCK_TIMEOUT_SECONDS
    fd = None

    while time.time() < deadline:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_RDWR)
            os.write(fd, str(os.getpid()).encode("utf-8"))
            return fd, lock_path
        except FileExistsError:
            time.sleep(CONFIG_LOCK_RETRY_SECONDS)
        except OSError:
            logger.exception("No se pudo crear lock de config | path=%s", lock_path)
            raise

    raise TimeoutError(f"No se pudo adquirir lock de config: {lock_path}")


def _release_config_lock(fd, lock_path: Path):
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        logger.warning("No se pudo eliminar lock de config | path=%s", lock_path)


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
    lock_fd = None
    lock_path = None

    try:
        lock_fd, lock_path = _acquire_config_lock(config_path.parent)
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
        last_error = None
        for _ in range(CONFIG_REPLACE_RETRIES):
            try:
                os.replace(temp_path, config_path)
                last_error = None
                break
            except PermissionError as exc:
                last_error = exc
                time.sleep(CONFIG_REPLACE_RETRY_SECONDS)
        if last_error is not None:
            raise last_error
        logger.debug("Config guardado correctamente | path=%s", config_path)
    except OSError:
        logger.exception("No se pudo guardar config.json | path=%s", config_path)
        raise
    except TimeoutError:
        logger.exception("Timeout esperando lock de config | path=%s", config_path)
        raise PermissionError(f"No se pudo obtener acceso exclusivo a {config_path}")
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
        _release_config_lock(lock_fd, lock_path) if lock_path else None
