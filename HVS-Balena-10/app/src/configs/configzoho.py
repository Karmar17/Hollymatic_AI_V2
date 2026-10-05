from src.configs.configs import config


class config_zoho:
    """
    Configuracion del flujo de autorizacion de dos pasos (Grima -> Zoho) y del
    envio del formulario "Encendido_Holymatic" en Zoho Creator.

    Reune, al estilo de config_rpi / config_composite, los valores que vienen del
    .env (via la clase `config`) para no dispersar os.getenv por el codigo.
    """

    # --- Paso 1: login en Grupo Grima ---
    GRIMA_AUTH_URL = config.GRIMA_AUTH_URL
    GRIMA_USERNAME = config.GRIMA_USERNAME
    GRIMA_PASSWORD = config.GRIMA_PASSWORD

    # --- Paso 2: ticket que devuelve el token de Zoho ---
    GRIMA_TICKET_URL = config.GRIMA_TICKET_URL
    ZOHO_ACCOUNT = config.ZOHO_ACCOUNT
    ZOHO_APPLICATION = config.ZOHO_APPLICATION

    # --- Paso 3/4: Zoho Creator (crear registro + subir imagenes) ---
    ZOHO_CREATOR_BASE = config.ZOHO_CREATOR_BASE
    ZOHO_OWNER = config.ZOHO_OWNER
    ZOHO_APP = config.ZOHO_APP
    ZOHO_FORM = config.ZOHO_FORM
    ZOHO_REPORT = config.ZOHO_REPORT

    ZOHO_FIELD_FRONTAL = config.ZOHO_FIELD_FRONTAL
    ZOHO_FIELD_CENITAL = config.ZOHO_FIELD_CENITAL
    ZOHO_FIELD_TRACERA = config.ZOHO_FIELD_TRACERA

    # Mapeo explicito vista-en-codigo -> link-name del campo en Zoho.
    # OJO: los nombres NO coinciden. El campo "Cenital" recibe la vista
    # "zenithal" y el campo "Tracera" recibe la vista "backward".
    VIEW_TO_ZOHO_FIELD = {
        "frontal":  ZOHO_FIELD_FRONTAL,
        "zenithal": ZOHO_FIELD_CENITAL,
        "backward": ZOHO_FIELD_TRACERA,
    }

    # Orden en el que se procesan/suben las vistas.
    VIEW_ORDER = ["frontal", "zenithal", "backward"]

    # Valor del campo de estado del registro recien creado.
    HOLLYMATIC_STATUS_FIELD = "Hollymatic"
    HOLLYMATIC_STATUS_VALUE = "Pendiente"
    HOLLYMATIC_ACTIVATE_FIELD = "ActivarHolly"
    HOLLYMATIC_ACTIVATE_VALUE = "Activate"

    HOLLYMATIC_DOMAIN_FIELD = "link_de_activaci_n"
    HOLLYMATIC_DOMAIN_VALUE = config.HOLLYMATIC_DOMAIN_VALUE

    HOLLYMATIC_BRANCH_FIELD = "Sucursal"
    HOLLYMATIC_BRANCH_VALUE = config.BRANCH

    # --- Cache de tokens y reintentos de red ---
    GRIMA_TOKEN_TTL = config.GRIMA_TOKEN_TTL
    ZOHO_TOKEN_TTL = config.ZOHO_TOKEN_TTL
    NET_MAX_RETRIES = config.NET_MAX_RETRIES
    NET_BACKOFF_BASE = config.NET_BACKOFF_BASE

    # Timeout por peticion (segundos), en linea con el resto del proyecto.
    REQUEST_TIMEOUT = 30
