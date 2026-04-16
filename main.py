__version__ = "1.11.0"

from core.logging.logger import ProjectLogger
from GUI.GUI_MAIN import GUI_MAIN


if __name__ == "__main__":
    ProjectLogger.configure(
        log_dir="logs",
        log_file="veripre.log",
        level=10,  # logging.DEBUG
        max_bytes=5 * 1024 * 1024,
        backup_count=5,
        console=True,
    )

    gui = GUI_MAIN(__version__)