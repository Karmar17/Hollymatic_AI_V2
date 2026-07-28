import logging
import inspect
import threading
import requests # Para enviar la petición a Google Chat
import traceback # Para formatear el stack trace
import datetime # Para el timestamp en la notificación de inicio

class GoogleChatHandler(logging.Handler):
    """
    Un logging Handler personalizado para enviar mensajes a un Webhook de Google Chat.
    """
    def __init__(self, webhook_url, level=logging.CRITICAL):
        super().__init__(level=level)
        self.webhook_url = webhook_url

    def format_record_for_chat(self, record):
        message_parts = []
        if record.levelname == "CRITICAL":
            message_parts.append(f"🚨 *{record.levelname}* 🚨")
        elif record.levelname == "ERROR":
             message_parts.append(f"🛑 *{record.levelname}*")
        elif record.levelname == "WARNING":
            message_parts.append(f"⚠️ *{record.levelname}*")
        else: # INFO, DEBUG, etc.
            message_parts.append(f"ℹ️ *{record.levelname}*")


        message_parts.append(f"*Logger:* `{record.name}`")
        message_parts.append(f"*Módulo:* `{record.module}.py` (Línea: {record.lineno})")
        if hasattr(record, 'threadName'):
             message_parts.append(f"*Hilo:* `{record.threadName}`")

        message_parts.append("\n*Mensaje:*")
        message_parts.append(f"```{record.getMessage()}```")

        if record.exc_info:
            exc_info_str = "".join(traceback.format_exception(*record.exc_info))
            max_trace_len = 2500
            if len(exc_info_str) > max_trace_len:
                exc_info_str = exc_info_str[:max_trace_len] + "\n... (traceback truncado)"
            message_parts.append("\n*Traceback:*")
            message_parts.append(f"```{exc_info_str}```")

        return "\n".join(message_parts)

    def emit(self, record):
        try:
            message = self.format_record_for_chat(record)
            payload = {"text": message}
            response = requests.post(self.webhook_url, json=payload, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            import sys
            sys.stderr.write(f"ERROR CRÍTICO DE LOGGING: Falló el envío a Google Chat: {e}\n"
                             f"Mensaje original: {record.getMessage()}\n")
        except Exception as e:
            import sys
            sys.stderr.write(f"ERROR CRÍTICO DE LOGGING: Error inesperado en GoogleChatHandler.emit: {e}\n"
                             f"Mensaje original: {record.getMessage()}\n")


class AppLogger:
    _loggers = {}
    _lock = threading.Lock()

    LEVELS = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }

    def __init__(
        self,
        name="app_logger",
        project_name=None, # Nuevo: Nombre del proyecto
        level="info",
        log_file=None,
        log_to_console=True,
        format_string="%(asctime)s - %(name)s [%(levelname)s] (%(threadName)s) - %(module)s:%(lineno)d - %(message)s",
        google_chat_webhook_url=None,
        google_chat_level="critical"
    ):
        self.logger = logging.getLogger(name)
        log_level_val = AppLogger.LEVELS.get(level.lower(), logging.INFO)
        self.logger.setLevel(log_level_val)
        
        self.name = name
        self.project_name = project_name # Almacenar el nombre del proyecto
        self.google_chat_webhook_url = google_chat_webhook_url

        if not self.logger.handlers:
            formatter = logging.Formatter(format_string)

            if log_to_console:
                ch = logging.StreamHandler()
                ch.setLevel(log_level_val)
                ch.setFormatter(formatter)
                self.logger.addHandler(ch)

            if log_file:
                try:
                    fh = logging.FileHandler(log_file, encoding='utf-8')
                    fh.setLevel(log_level_val)
                    fh.setFormatter(formatter)
                    self.logger.addHandler(fh)
                except IOError as e:
                    print(f"ERROR CONFIG LOGGING: No se pudo abrir el archivo de log {log_file} para '{name}': {e}")
            
            if google_chat_webhook_url:
                try:
                    gchat_level_val = AppLogger.LEVELS.get(google_chat_level.lower(), logging.CRITICAL)
                    gchat_handler = GoogleChatHandler(google_chat_webhook_url, level=gchat_level_val)
                    self.logger.addHandler(gchat_handler)
                except Exception as e:
                    print(f"ERROR CONFIG LOGGING: No se pudo configurar GoogleChatHandler para '{name}': {e}")

    # --- Métodos de logging estándar ---
    def debug(self, message, *args, exc_info=False, stack_info=False, **kwargs):
        self.logger.debug(message, *args, exc_info=exc_info, stack_info=stack_info, stacklevel=2, **kwargs)

    def info(self, message, *args, exc_info=False, stack_info=False, **kwargs):
        self.logger.info(message, *args, exc_info=exc_info, stack_info=stack_info, stacklevel=2, **kwargs)

    def warning(self, message, *args, exc_info=False, stack_info=False, **kwargs):
        self.logger.warning(message, *args, exc_info=exc_info, stack_info=stack_info, stacklevel=2, **kwargs)

    def error(self, message, *args, exc_info=True, stack_info=False, **kwargs):
        self.logger.error(message, *args, exc_info=exc_info, stack_info=stack_info, stacklevel=2, **kwargs)

    def critical(self, message, *args, exc_info=True, stack_info=False, **kwargs):
        self.logger.critical(message, *args, exc_info=exc_info, stack_info=stack_info, stacklevel=2, **kwargs)

    # --- Método para log de inicialización ---
    def log_startup(self, message, *args, **kwargs):
        """
        Registra un mensaje de inicialización.
        Siempre se loguea como INFO. Si el nivel efectivo del logger NO es DEBUG
        y hay un webhook de Google Chat configurado, envía una notificación a Chat
        incluyendo el nombre del proyecto si está definido.
        """
        self.logger.info(message, *args, stacklevel=2, **kwargs)

        if self.google_chat_webhook_url and self.logger.getEffectiveLevel() > logging.DEBUG:
            try:
                final_message = message
                if args:
                    final_message = message % args
                
                timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S %Z")
                
                # Identificador del proyecto para el mensaje de Chat
                if self.project_name:
                    header_title = f"PROYECTO '{self.project_name}' INICIADO"
                else:
                    header_title = "PROGRAMA INICIADO"

                chat_message_payload = (
                    f"🚀 *{header_title}* 🚀\n"
                    f"-------------------------------------\n"
                    f"*Logger:* `{self.name}`\n"
                    f"*Timestamp:* {timestamp}\n"
                    f"*Mensaje:* {final_message}\n"
                    f"-------------------------------------\n"
                    f"Modo actual: {logging.getLevelName(self.logger.getEffectiveLevel())} (No DEBUG)"
                )
                
                payload = {"text": chat_message_payload}
                response = requests.post(self.google_chat_webhook_url, json=payload, timeout=10)
                response.raise_for_status()
                
                self.logger.debug(f"Notificación de inicio para '{self.name}' enviada a Google Chat.", stacklevel=2)
            
            except requests.exceptions.RequestException as e:
                self.logger.error(
                    f"Falló el envío de notificación de inicio a Google Chat para '{self.name}': {e}", 
                    exc_info=False,
                    stacklevel=2
                )
            except Exception as e:
                self.logger.error(
                    f"Error inesperado al enviar notificación de inicio a Google Chat para '{self.name}': {e}",
                    exc_info=True,
                    stacklevel=2
                )
                
    @staticmethod
    def get_logger(name="app_logger", **kwargs): # project_name se pasará por kwargs
        """
         Considerar reconfiguración si es necesario. Por ahora, retorna existente.
         Considera un unico project_name UNICO para cada inicializacion. (Preferible que todo el proyecto maneje el mismo).
         
        """
        with AppLogger._lock:
            if name in AppLogger._loggers:
            #Esta paso valida el nombre del proyecto en la cual hace referencia el proyecto.
                return AppLogger._loggers[name]
            else:
                new_logger_instance = AppLogger(name=name, **kwargs)
                AppLogger._loggers[name] = new_logger_instance
                return new_logger_instance