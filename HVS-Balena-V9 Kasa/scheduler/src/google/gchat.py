import time
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.configs.settings import config

class gchat:

    def send_advice(message_content):
        service_account_path = config.SERVICE_ACCOUNT_PATH
        space_id = config.SPACE_ID
        count = 0
        chatresponse = gchat.send_message_to_space(service_account_path, space_id, message_content)
        if chatresponse == None:
            while chatresponse == None and count < 10:
             time.sleep(1200)
             chatresponse = gchat.send_message_to_space(service_account_path, space_id, message_content)
             count = count + 1

        time.sleep(10)



        return 0

    def send_message_to_space(service_account_path, spaceID, message_content):

        """
        Envía un mensaje de texto simple a un espacio específico de Google Chat
        utilizando credenciales de cuenta de servicio.

        Args:
            service_account_path (str): Ruta al archivo JSON de la clave de cuenta de servicio.
            spaceID (str): El ID del espacio de destino (formato: 'spaces/AAAAxxxxxxx').
            message_content (str): El texto del mensaje a enviar.

        Returns:
            dict: La respuesta de la API si el mensaje se envió correctamente, None si hubo un error.
        """
        SCOPES = ['https://www.googleapis.com/auth/chat.bot']
        logger = logging.getLogger(__name__)
        try:
            # --- Autenticación ---
            credentials = service_account.Credentials.from_service_account_file(
                service_account_path, scopes=SCOPES)

            # Construir el servicio de la API de Chat
            chat_service = build('chat', 'v1', credentials=credentials)

            # --- Preparar la Solicitud ---
            # El 'parent' es el ID del espacio donde se creará el mensaje
            parent_resource = f"spaces/{spaceID.replace('spaces/', '')}" # Asegura el formato correcto

            # Cuerpo del mensaje (simple texto)
            message_body = {
                'text': message_content
            }

            # --- Enviar el Mensaje ---
            logger.info(f"Enviando mensaje al espacio: {parent_resource}")
            logger.info(f"Enviando mensaje al espacio: {parent_resource}")
            request = chat_service.spaces().messages().create(
                parent=parent_resource,
                body=message_body
            )
            response = request.execute()

            logger.info(f"   - Mensaje enviado con éxito. ID del mensaje: {response.get('name')}")
            logger.info(f"   - Mensaje enviado con éxito. ID del mensaje: {response.get('name')}")
            # logger.info(f"Respuesta completa: {response}") # Descomenta para ver toda la respuesta
            return response

        except HttpError as error:
            logger.error(f"Ocurrió un error al enviar el mensaje: {error}")
            logger.error(f"   ->Ocurrió un error al enviar el mensaje: {error}")
            # El contenido del error a menudo tiene más detalles
            try:
                error_details = error.resp.reason
                error_content = error.content.decode()
                logger.error(f"Razón del error: {error_details}")
                logger.error(f"   ->Razón del error: {error_details}")
                logger.error(f"Contenido del error: {error_content}")
                logger.error(f"   ->Contenido del error: {error_content}")
            except Exception:
                logger.error(f"Detalles adicionales del error: {error.content}")
                logger.error(f"   ->Detalles adicionales del error: {error.content}")
            return None
        except FileNotFoundError:
            logger.error(f"Error: No se encontró el archivo de clave de cuenta de servicio en '{service_account_path}'")
            logger.error(f"   ->Error: No se encontró el archivo de clave de cuenta de servicio en '{service_account_path}'")
            logger.error("Asegúrate de que la ruta sea correcta.")
            logger.error("   ->Asegúrate de que la ruta sea correcta.")
            return None
        except Exception as e:
            logger.error(f"Ocurrió un error inesperado: {e}")
            logger.error(f"   -> Ocurrió un error inesperado: {e}")
            return None
