import os
from src.configs.settings import config
from src.utils.applogger import AppLogger

class logger_config:

    GOOGLE_CHAT_WEBHOOK_URL = config.GOOGLE_CHAT_WEBHOOK_URL
    #GOOGLE_CHAT_WEBHOOK_URL = None
    ROOT_PROYECT_NAME = config.ROOT_PROYECT_NAME
    MAIN_LOG_FILE = config.MAIN_LOG_FILE
    CORE_NAME_MAIN = config.CORE_NAME_MAIN

    main_production_logger = AppLogger.get_logger(
            name= CORE_NAME_MAIN ,
            project_name=ROOT_PROYECT_NAME, 
            level="info",
            log_file= MAIN_LOG_FILE,
            google_chat_webhook_url=GOOGLE_CHAT_WEBHOOK_URL,
            google_chat_level="critical"
        )