from logging import config as log_config, getLogger

from src.app import LOGGING_CONFIG, PostgresToEsApplication
from src.utils import AppConfigDC


def main():
    app_config = AppConfigDC()
    log_config.dictConfig(LOGGING_CONFIG)
    logger = getLogger(app_config.logger_name)
    logger.setLevel(app_config.log_level)
    app = PostgresToEsApplication(app_config, logger)
    app.run()


if __name__ == "__main__":
    main()
