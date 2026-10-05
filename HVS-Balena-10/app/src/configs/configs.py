import os
from dotenv import load_dotenv

class config:
    load_dotenv()

    #===================== CAMERA SELECTOR ========================#
    CLASSIFICATION_MODEL_PATH = os.getenv("CLASSIFICATION_MODEL_PATH")

    #===================== QA MODEL PATHS ========================#
    LOCK_SHAFT_MODEL_PATH = os.getenv("LOCK_SHAFT_MODEL_PATH")
    KO_CUP_MODEL_PATH = os.getenv("KO_CUP_MODEL_PATH")
    ECCENTRIC_LEVER_AND_KO_CUP_MODEL_PATH = os.getenv("ECCENTRIC_LEVER_AND_KO_CUP_MODEL_PATH")
    ZENITHAL_ASSEMBLY_MODEL_PATH = os.getenv("ZENITHAL_ASSEMBLY_MODEL_PATH")
    RAM_ASSEMBLY_AND_DRIVE_BAR_MODEL_PATH = os.getenv("RAM_ASSEMBLY_AND_DRIVE_BAR_MODEL_PATH")
    LOCK_PIN_MODEL_PATH = os.getenv("LOCK_PIN_MODEL_PATH")

    #===================== GENERAL CONFIGURATIONS ========================#
    STRING_CAMERA_PATHS = os.getenv("CAMERA_PATHS")
    CAMERA_PATHS = STRING_CAMERA_PATHS.split(",")
    STRING_FOCUS_THRESHOLD = os.getenv("FOCUS_THRESHOLD")
    FOCUS_THRESHOLD = float(STRING_FOCUS_THRESHOLD)
    STRING_BRIGHTNESS_THRESHOLD = os.getenv("BRIGHTNESS_THRESHOLD")
    BRIGHTNESS_THRESHOLD = float(STRING_BRIGHTNESS_THRESHOLD)
    STRING_BBOX_MAX_ASPECT_RATIO = os.getenv("BBOX_MAX_ASPECT_RATIO")
    BBOX_MAX_ASPECT_RATIO = float(STRING_BBOX_MAX_ASPECT_RATIO)
    STRING_MIN_CONFIDENCE = os.getenv("MIN_CONFIDENCE")
    MIN_CONFIDENCE = float(STRING_MIN_CONFIDENCE)
    BRANCH = os.getenv("BRANCH")

    #===================== GOOGLE CONFIGURATIONS ========================#
    SERVICE_ACCOUNT_PATH = os.getenv("SERVICE_ACCOUNT_PATH")
    SPACE_ID = os.getenv("SPACE_ID")
    # Carpeta destino en Drive para el PDF comparativo (recomendado: una
    # Unidad Compartida a la que el service-account tenga acceso de escritura).
    DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID")

    #===================== MIKASA CONFIGURATIONS ========================#
    MIKASA_IP = os.getenv("MIKASA_IP")
    MIKASA_USERNAME = os.getenv("MIKASA_USERNAME")
    MIKASA_PASSWORD = os.getenv("MIKASA_PASSWORD")

    #===================== DATABASE CONFIGURATIONS ========================#
    # El `app` registra los intentos en el contenedor `db`, alcanzable por la red
    # interna de Docker (resolución por nombre de servicio; sin exponer el puerto).
    DB_HOST = os.getenv("DB_HOST", "db")
    DB_PORT = int(os.getenv("DB_PORT", "3306"))
    DB_NAME = os.getenv("DB_NAME", "hollymatic")
    DB_USER = os.getenv("DB_USER", "hollymatic")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")

    #==================== APP LOGGER CONFIGURATIONS ======================#
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv('GOOGLE_CHAT_WEBHOOK_URL')
    ROOT_PROYECT_NAME = os.getenv('ROOT_PROYECT_NAME')
    MAIN_LOG_FILE = os.getenv('MAIN_LOG_FILE')
    CORE_NAME_MAIN = os.getenv('CORE_NAME_MAIN')

    #=================== RASPBERRY CONFIGURATIONS =======================#
    STRING_SHUT_DOWN_PIN = os.getenv("SHUT_DOWN_PIN")
    SHUT_DOWN_PIN = int(STRING_SHUT_DOWN_PIN)
    STRING_TURN_ON_PIN = os.getenv("TURN_ON_PIN")
    TURN_ON_PIN = int(STRING_TURN_ON_PIN)
    STRING_CALIBRATE_PIN = os.getenv("CALIBRATE_PIN")
    CALIBRATE_PIN = int(STRING_CALIBRATE_PIN)

    #=================== ZOHO / GRIMA CONFIGURATIONS =====================#
    # Autorizacion de dos pasos contra Grupo Grima -> token Zoho -> envio del
    # formulario de encendido en Zoho Creator (reemplaza la calibracion fisica).
    GRIMA_AUTH_URL = os.getenv("GRIMA_AUTH_URL")
    GRIMA_USERNAME = os.getenv("GRIMA_USERNAME")
    GRIMA_PASSWORD = os.getenv("GRIMA_PASSWORD")
    GRIMA_TICKET_URL = os.getenv("GRIMA_TICKET_URL")

    ZOHO_ACCOUNT = os.getenv("ZOHO_ACCOUNT")
    ZOHO_APPLICATION = os.getenv("ZOHO_APPLICATION")
    ZOHO_CREATOR_BASE = os.getenv("ZOHO_CREATOR_BASE")
    ZOHO_OWNER = os.getenv("ZOHO_OWNER")
    ZOHO_APP = os.getenv("ZOHO_APP")
    ZOHO_FORM = os.getenv("ZOHO_FORM")
    ZOHO_REPORT = os.getenv("ZOHO_REPORT")

    # Link-names de los campos de imagen en Zoho (OJO: distintos del nombre de la
    # vista en el codigo -> Frontal<-frontal, Cenital<-zenithal, Tracera<-backward).
    ZOHO_FIELD_FRONTAL = os.getenv("ZOHO_FIELD_FRONTAL")
    ZOHO_FIELD_CENITAL = os.getenv("ZOHO_FIELD_CENITAL")
    ZOHO_FIELD_TRACERA = os.getenv("ZOHO_FIELD_TRACERA")
    
    HOLLYMATIC_DOMAIN_VALUE = os.getenv("HOLLYMATIC_DOMAIN_VALUE")

    # Cache de tokens (segundos) y politica de reintentos de red.
    GRIMA_TOKEN_TTL = int(os.getenv("GRIMA_TOKEN_TTL", "3300"))
    ZOHO_TOKEN_TTL = int(os.getenv("ZOHO_TOKEN_TTL", "3300"))
    NET_MAX_RETRIES = int(os.getenv("NET_MAX_RETRIES", "3"))
    NET_BACKOFF_BASE = float(os.getenv("NET_BACKOFF_BASE", "1"))

    #======================= HOLLYMATIC MESSAGES ========================#
    HOLLYMATIC_MESSAGE_START = os.getenv('HOLLYMATIC_MESSAGE_START')
    HOLLYMATIC_MESSAGE_CORRECT_ASSEMBLY = os.getenv('HOLLYMATIC_MESSAGE_CORRECT_ASSEMBLY')
    HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_GREATING = os.getenv('HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_GREATING')
    HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_DEPATURE = os.getenv('HOLLYMATIC_MESSAGE_BAD_ASSEMBLY_DEPATURE')

    HOLLYMATIC_MESSAGE_MANDATORY_SOLUTIONS = os.getenv('HOLLYMATIC_MESSAGE_MANDATORY_SOLUTIONS')
    HOLLYMATIC_MESSAGE_CALIBRATE_START = os.getenv('HOLLYMATIC_MESSAGE_CALIBRATE_START')
    HOLLYMATIC_MESSAGE_CALIBRATE_END = os.getenv('HOLLYMATIC_MESSAGE_CALIBRATE_END')
    HOLLYMATIC_MESSAGE_SHUT_DOWN = os.getenv('HOLLYMATIC_MESSAGE_SHUT_DOWN')

