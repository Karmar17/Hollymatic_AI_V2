import os
import datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from src.configs.settings import config
from src.configs.configlogger import logger_config


class gdrive:
    """
    Subida del PDF de KPIs a Google Drive y obtencion de un link compartible
    ("cualquiera con el link"). Reutiliza la misma cuenta de servicio que gchat.py.
    Es una copia del gdrive del contenedor `app` (ambos codigos son separados).
    """

    @staticmethod
    def upload_and_get_link(file_path):
        """
        Sube `file_path` (PDF) a Drive, lo comparte como lector publico y
        retorna su webViewLink. Retorna None ante cualquier error para no
        bloquear el envio del mensaje de texto.
        """
        SCOPES = ['https://www.googleapis.com/auth/drive']
        logger = logger_config.main_production_logger

        if not file_path or not os.path.exists(file_path):
            logger.critical(f"No se puede subir a Drive: archivo inexistente '{file_path}'")
            return None

        folder_id = getattr(config, 'DRIVE_FOLDER_ID', None)
        remote_name = f"hollymatic_kpi_{datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.pdf"

        try:
            credentials = service_account.Credentials.from_service_account_file(
                config.SERVICE_ACCOUNT_PATH, scopes=SCOPES)

            drive_service = build('drive', 'v3', credentials=credentials)

            file_metadata = {'name': remote_name}
            if folder_id:
                file_metadata['parents'] = [folder_id]
            else:
                logger.critical(
                    "DRIVE_FOLDER_ID no configurado; se intentara subir sin carpeta destino "
                    "(las cuentas de servicio sin Unidad Compartida suelen fallar por cuota).")

            media = MediaFileUpload(file_path, mimetype='application/pdf', resumable=False)

            created = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True,
            ).execute()

            file_id = created.get('id')

            # Compartir como "cualquiera con el link" (lector).
            drive_service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'},
                supportsAllDrives=True,
            ).execute()

            link = created.get('webViewLink')
            logger.info(f"PDF de KPIs subido a Drive. Link: {link}")
            return link

        except HttpError as error:
            logger.critical(f"Error de la API de Drive al subir el PDF de KPIs: {error}")
            return None
        except FileNotFoundError:
            logger.critical(
                f"No se encontro el archivo de cuenta de servicio en '{config.SERVICE_ACCOUNT_PATH}'")
            return None
        except Exception as e:
            logger.critical(f"Error inesperado al subir el PDF de KPIs a Drive: {e}")
            return None
