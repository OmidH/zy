import logging


class CustomFormattedLogger(logging.Formatter):
    """Log Formatter that inserts ANSI color codes for different logging levels."""
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    light_blue = "\x1b[94m"
    red = "\x1b[31;21m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "%(asctime)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: light_blue + format + reset,
        logging.INFO: light_blue + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def getLogger():
    logger_name = 'custom_app_logger'
    logger = logging.getLogger(logger_name)

    # Ensure that logger does not duplicate handlers on multiple calls
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(CustomFormattedLogger())
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

    return logger
