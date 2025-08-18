from loguru import logger
import sys


class Logger:
    def __init__(self):
        self.logger = logger
        self.logger.remove()

        # Formato per DEBUG e ERROR (dettagliato con file:riga)
        detailed_format = (
            "<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | "
            "<cyan>{file}:{line}</cyan> - <level>{message}</level>"
        )

        # Formato per INFO con livello verde e grassetto, messaggio verde
        info_format = (
            "<green>{time:HH:mm:ss}</green> | <bold><green>{level:<8}</green></bold> | <green>{message}</green>"
        )

        # Handler per DEBUG ed ERROR
        self.logger.add(
            sys.stderr,
            format=detailed_format,
            level="DEBUG",
            filter=lambda r: r["level"].name in ["DEBUG", "ERROR"],
            colorize=True
        )

        # Handler per INFO
        self.logger.add(
            sys.stderr,
            format=info_format,
            level="INFO",
            filter=lambda r: r["level"].name == "INFO",
            colorize=True
        )

        # Handler per WARNING e CRITICAL
        self.logger.add(
            sys.stderr,
            format=detailed_format,
            level="WARNING",
            filter=lambda r: r["level"].name in ["WARNING", "CRITICAL"],
            colorize=True
        )

    def debug(self, message: str):
        self.logger.debug(message)

    def info(self, message: str):
        self.logger.info(message)

    def error(self, message: str):
        self.logger.error(message)

    def warning(self, message: str):
        self.logger.warning(message)