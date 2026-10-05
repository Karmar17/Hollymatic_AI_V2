import os
import cv2
import datetime
from src.configs.configcamera import camera_configurations
from src.configs.configlogger import logger_config
from src.utils.camerautils import cameraUtils


class imager:
    def __init__(self):
        """
        Inicializa el modulo de control de imagenes y capturas
        """
        self.logger = logger_config.main_production_logger
        self.camera_utils = cameraUtils()

        pass

    def capture_image(self = None,camera_path = None, output_dir = "captures"):
        """
        Captura una imagen desde la cámara especificada.

        Parámetros:
            camera_path (str): Path del dispositivo de la cámara
            output_dir (str): Directorio para guardar la imagen

        Retorna:path
            str: Path de la imagen guardada o None si falla
        """
        subfolder = datetime.datetime.now().strftime('%Y-%m-%d')
        imagename = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+".jpeg"
        camera_path = str(camera_path)

        if not os.path.exists(camera_path):
            self.logger.error(f"Error: Cámara no encontrada en {camera_path}")

        # Crear directorio si no existe
        try:
            img_path = self.save_in_folder("captures",subfolder,imagename)
        except Exception as e:
            self.logger.error(f"No se ha podido crear el directorio {output_dir} debido a: {e}")
        except:
            self.logger.error(f"No se ha podifo crear el directorio {output_dir} debido a un error no reconocido")


        try:
            self.logger.info("Se configura la visualizacion de la camara")
            cap = camera_configurations.set(camera_path)

        except Exception as e:
            print(f"Error al setear la camara debido a:{e}")

        except:
            print("Error al setear la camara debido a un error desconocido")

        try:
            # Capturar imagen
            self.logger.info(f"Tomando imagen en el path: {img_path}")
            self.camera_utils.capture_image(img_path,cap)

            return img_path

        finally:
            cap.release()
            cv2.destroyAllWindows()

    @staticmethod
    def save_in_folder(imagesfolder,subfolder,imagename):
        # Crear la carpeta principal si no existe
        if not os.path.exists(imagesfolder):
            os.makedirs(imagesfolder)

        # Ruta de la carpeta para el tipo de objeto
        object_folder = os.path.join(imagesfolder, subfolder)

        # Validar explícitamente si la carpeta del tipo de objeto ya existe
        if not os.path.exists(object_folder):
            os.makedirs(object_folder)
        #else:
            #print(f"La carpeta para el tipo de objeto '{trackObject}' ya existe.")

        # Construir la ruta completa del archivo
        frame_path = os.path.join(object_folder, imagename)
        
        return frame_path