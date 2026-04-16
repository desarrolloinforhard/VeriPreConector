import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


class ProjectLogger:
    """
    Logger centralizado del proyecto.

    - Consola + archivo
    - Rotación automática
    - Reutilizable por módulo
    - Evita handlers duplicados
    """

    _configured = False
    _log_dir: Optional[Path] = None
    _default_level = logging.DEBUG

    @classmethod
    def configure(
        cls,
        log_dir: str = "logs",
        log_file: str = "veripre.log",
        level: int = logging.DEBUG,
        max_bytes: int = 5 * 1024 * 1024,
        backup_count: int = 5,
        console: bool = True,
    ) -> None:
        """
        Configura el logger raíz del proyecto una sola vez.
        """
        if cls._configured:
            return

        cls._default_level = level
        cls._log_dir = Path(log_dir)
        cls._log_dir.mkdir(parents=True, exist_ok=True)

        root_logger = logging.getLogger("veripre")
        root_logger.setLevel(level)
        root_logger.propagate = False

        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Handler de archivo con rotación
        file_handler = RotatingFileHandler(
            cls._log_dir / log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        # Handler de consola
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)

        cls._configured = True

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """
        Devuelve un logger hijo por módulo.
        """
        if not cls._configured:
            cls.configure()

        return logging.getLogger(f"veripre.{module_name}")


def get_logger(module_name: str) -> logging.Logger:
    """
    Helper simple para importar directo:
    from core.logging.logger import get_logger
    """
    return ProjectLogger.get_logger(module_name)