import os
import time

import requests

from src.configs.configzoho import config_zoho
from src.configs.configlogger import logger_config
from src.executors.assembly_composite import assembly_composite


class ZohoEncendidoProxy:
    """
    Proxy de autorizacion de dos pasos (Grupo Grima) que crea un registro
    "Pendiente" en el formulario de encendido de Zoho Creator y adjunta las
    imagenes clasificadas de la ultima corrida.

    Flujo (ver plan):
      1. Login en Grima            -> token_grima
      2. getTicket (Bearer grima)  -> token_zoho
      3. Crear registro en el form -> record_id
      4. Subir cada imagen clasificada al campo correspondiente del registro.

    - Tokens cacheados en memoria con expiracion temporal (se reutilizan mientras
      esten vigentes; se re-solicitan al expirar o ante un 401).
    - Toda salida de red pasa por `_request_with_retries` (>= NET_MAX_RETRIES
      reintentos ante fallos transitorios: timeout, conexion, 429, 5xx).
    - Ningun fallo tumba el loop principal: se loguea critical y se retorna.
    """

    logger = logger_config.main_production_logger

    def __init__(self):
        self._grima_token = None
        self._grima_token_exp = 0.0
        self._zoho_token = None
        self._zoho_token_exp = 0.0

    # ------------------------------------------------------------------ #
    #  Helper de red con reintentos 
    # ------------------------------------------------------------------ #
    def _request_with_retries(self, method, url, **kwargs):
        """
        Ejecuta requests.request con >= NET_MAX_RETRIES reintentos ante fallos
        transitorios (excepciones de red, HTTP 429 y 5xx). Backoff exponencial:
        NET_BACKOFF_BASE * 2**intento. Retorna el Response ante exito o error no
        reintentable (p.ej. 4xx). Lanza RuntimeError si se agotan los reintentos.
        """
        kwargs.setdefault("timeout", config_zoho.REQUEST_TIMEOUT)
        attempts = config_zoho.NET_MAX_RETRIES + 1  # 1 intento inicial + N reintentos
        last_error = None

        for attempt in range(attempts):
            try:
                response = requests.request(method, url, **kwargs)
                # 429 y 5xx se consideran transitorios -> reintentar.
                if response.status_code != 200:
                    last_error = f"HTTP {response.status_code} en {url}"
                    self.logger.warning(
                        f"Respuesta transitoria ({response.status_code}) de {url}; "
                        f"intento {attempt + 1}/{attempts}")
                else:
                    return response
            except requests.exceptions.RequestException as e:
                last_error = e
                self.logger.warning(
                    f"Fallo de red hacia {url}: {e}; intento {attempt + 1}/{attempts}")

            # Si aun quedan reintentos, esperar con backoff exponencial.
            if attempt < attempts - 1:
                time.sleep(config_zoho.NET_BACKOFF_BASE * (2 ** attempt))

        raise RuntimeError(
            f"Se agotaron los {attempts} intentos hacia {url}. Ultimo error: {last_error}")

    # ------------------------------------------------------------------ #
    #  Paso 1: token de Grima (con cache + expiracion)
    # ------------------------------------------------------------------ #
    def _get_grima_token(self, force=False):
        if not force and self._grima_token and time.time() < self._grima_token_exp:
            return self._grima_token

        response = self._request_with_retries(
            "POST",
            config_zoho.GRIMA_AUTH_URL,
            json={
                "username": config_zoho.GRIMA_USERNAME,
                "password": config_zoho.GRIMA_PASSWORD,
            },
        )
        payload = response.json()
        if not payload.get("success") or "token" not in payload.get("data", {}):
            raise RuntimeError(f"Login Grima fallido (HTTP {response.status_code}): {payload}")

        self._grima_token = payload["data"]["token"]
        self._grima_token_exp = time.time() + config_zoho.GRIMA_TOKEN_TTL
        self.logger.info("Token Grima obtenido y cacheado")
        return self._grima_token

    # ------------------------------------------------------------------ #
    #  Paso 2: token de Zoho (con cache + expiracion)
    # ------------------------------------------------------------------ #
    def _get_zoho_token(self, force=False):
        if not force and self._zoho_token and time.time() < self._zoho_token_exp:
            return self._zoho_token

        # Un 401 aqui implica token Grima invalido -> refrescar Grima y reintentar 1 vez.
        for grima_force in (False, True):
            grima_token = self._get_grima_token(force=grima_force)
            response = self._request_with_retries(
                "POST",
                config_zoho.GRIMA_TICKET_URL,
                headers={"Authorization": f"Bearer {grima_token}"},
                json={
                    "account": config_zoho.ZOHO_ACCOUNT,
                    "application": config_zoho.ZOHO_APPLICATION,
                },
            )
            if response.status_code == 401 and not grima_force:
                self.logger.warning("getTicket devolvio 401; refrescando token Grima")
                continue

            payload = response.json()
            if not payload.get("success") or "token" not in payload.get("data", {}):
                raise RuntimeError(f"getTicket fallido (HTTP {response.status_code}): {payload}")

            self._zoho_token = payload["data"]["token"]
            self._zoho_token_exp = time.time() + config_zoho.ZOHO_TOKEN_TTL
            self.logger.info("Token Zoho obtenido y cacheado")
            return self._zoho_token

        raise RuntimeError("No se pudo obtener el token Zoho tras refrescar el token Grima")

    #  Peticion autorizada a Zoho Creator (maneja 401 -> refresco de token)

    def _zoho_request(self, method, url, **kwargs):
        for zoho_force in (False, True):
            token = self._get_zoho_token(force=zoho_force)
            headers = dict(kwargs.pop("headers", {}))
            headers["Authorization"] = f"Zoho-oauthtoken {token}"
            response = self._request_with_retries(method, url, headers=headers, **kwargs)
            if response.status_code == 401 and not zoho_force:
                self.logger.warning(f"Zoho devolvio 401 en {url}; refrescando token Zoho")
                continue
            return response
        return response

    @staticmethod
    def _extract_record_id(payload):
        """
        Extrae el record ID de la respuesta del add-records v2.1. Shape real:
            {"result":[{"code":3000,"data":{"ID":"..."}}], "code":3000}
        Con fallbacks para {"data":{"ID":...}} y {"data":[{"ID":...}]}.
        """
        result = payload.get("result")
        if isinstance(result, list) and result:
            entry = result[0]
            data = entry.get("data") if isinstance(entry, dict) else None
            if isinstance(data, dict) and data.get("ID"):
                return data.get("ID")

        data = payload.get("data")
        if isinstance(data, list):
            data = data[0] if data else {}
        if isinstance(data, dict):
            return data.get("ID")
        return None

    # ------------------------------------------------------------------ #
    #  Paso 3: crear el registro "Pendiente" y devolver el record_id
    # ------------------------------------------------------------------ #
    def _create_record(self):
        url = (f"{config_zoho.ZOHO_CREATOR_BASE}/data/{config_zoho.ZOHO_OWNER}/"
               f"{config_zoho.ZOHO_APP}/form/{config_zoho.ZOHO_FORM}")
        # `data` es un arreglo de REGISTROS: cada dict = un registro. Los tres
        # campos van en UN SOLO registro. Si se mandan como tres dicts separados
        # se crean tres registros y en los que no llevan el campo "Hollymatic"
        # Zoho aplica el valor por defecto del formulario ("Aprobado"), en vez de
        # dejar el "Pendiente" que exige la autorizacion de dos pasos.
        body = {
            "data": [
                {
                    config_zoho.HOLLYMATIC_STATUS_FIELD: config_zoho.HOLLYMATIC_STATUS_VALUE,
                    config_zoho.HOLLYMATIC_ACTIVATE_FIELD: config_zoho.HOLLYMATIC_ACTIVATE_VALUE,
                    config_zoho.HOLLYMATIC_DOMAIN_FIELD: config_zoho.HOLLYMATIC_DOMAIN_VALUE,
                    config_zoho.HOLLYMATIC_BRANCH_FIELD: config_zoho.HOLLYMATIC_BRANCH_VALUE,
                }
            ]
        }
        response = self._zoho_request("POST", url, json=body)
        payload = response.json()

        # Shape REAL verificado contra el endpoint:
        #   {"result":[{"code":3000,"data":{"ID":"..."},"message":"Data Added Successfully"}],"code":3000}
        # Zoho puede responder HTTP 200 con un code de error, asi que validamos el
        # code interno ademas del status y del ID.
        result_code = None
        result = payload.get("result")
        if isinstance(result, list) and result and isinstance(result[0], dict):
            result_code = result[0].get("code")

        record_id = self._extract_record_id(payload)
        if response.status_code >= 400 or (result_code is not None and result_code != 3000) or not record_id:
            raise RuntimeError(
                f"No se pudo crear el registro (HTTP {response.status_code}, code={result_code}): {payload}")

        self.logger.info(f"Registro de encendido creado en Zoho Creator: ID={record_id}")
        return record_id

    # ------------------------------------------------------------------ #
    #  Paso 4: subir una imagen a un campo del registro
    # ------------------------------------------------------------------ #
    def _upload_image(self, record_id, field_link_name, image_path):
        url = (f"{config_zoho.ZOHO_CREATOR_BASE}/data/{config_zoho.ZOHO_OWNER}/"
               f"{config_zoho.ZOHO_APP}/report/{config_zoho.ZOHO_REPORT}/"
               f"{record_id}/{field_link_name}/upload")
        with open(image_path, "rb") as fh:
            files = {"file": (os.path.basename(image_path), fh, "image/jpeg")}
            response = self._zoho_request("POST", url, files=files)

        # Shape REAL verificado:
        #   {"code":3000,"data":{"filename":"frontal.jpeg","message":"File Uploaded Successfully"}}
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        code = payload.get("code")

        if response.status_code >= 400 or (code is not None and code != 3000):
            self.logger.critical(
                f"Fallo al subir '{image_path}' al campo '{field_link_name}' "
                f"(HTTP {response.status_code}, code={code}): {response.text}")
            return False

        message = (payload.get("data") or {}).get("message", "File Uploaded Successfully")
        self.logger.info(
            f"Imagen '{os.path.basename(image_path)}' subida al campo '{field_link_name}' ({message})")
        return True

    # ------------------------------------------------------------------ #
    #  Orquestacion completa 
    # ------------------------------------------------------------------ #
    def send_encendido(self):
        """
        Ejecuta el flujo completo. Crea el registro aunque no haya ninguna imagen
        clasificada; las vistas sin imagen simplemente no se suben (campo vacio).
        Cualquier error se loguea como critical y no propaga (no tumba el loop).
        """
        try:
            record_id = self._create_record()

            for view in config_zoho.VIEW_ORDER:
                field_link_name = config_zoho.VIEW_TO_ZOHO_FIELD.get(view)
                image_path = assembly_composite.view_frame_path(view)
                if not image_path:
                    self.logger.info(
                        f"Vista '{view}' sin imagen clasificada; se omite (campo '{field_link_name}' vacio)")
                    continue
                self._upload_image(record_id, field_link_name, image_path)

            self.logger.info("Flujo de encendido enviado a Zoho Creator")
            return record_id

        except Exception as e:
            self.logger.critical(f"No se pudo completar la solicitud de encendido a Zoho debido a: {e}")
            return None
