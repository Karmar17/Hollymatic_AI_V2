import os
import cv2
import time
import pyudev
import numpy as np
from typing import Dict
from src.configs.configlogger import logger_config
from src.configs.configcamera import camera_configurations



class cameraUtils: 
    
    def __init__(self):
        self.logger = logger_config.main_production_logger
        pass

  
    def check_cameras(self) -> Dict[str, Dict]:
        """
        Verifica el estado de las cámaras en los paths predefinidos.

        Retorna:
            Dict: Diccionario con información de cada cámara
        """
        context = pyudev.Context()
        cameras = camera_configurations.CAMERAS

        for path in camera_configurations.CAMERA_PATHS:
            self.logger.info(f"Se detecta si la camara correspondiente al {path} se encuentra disponible")
            
            cam_info = {'path': path, 'exists': False}

            if os.path.exists(path):
                cam_info['exists'] = True
                try:
                    device = pyudev.Devices.from_device_file(context, path)
                    cam_info['id_serial'] = device.get('ID_SERIAL', 'No disponible')
                except Exception as e:
                    cam_info['error'] = str(e)

            camera_configurations.CAMERAS[path] = cam_info
            

        return cameras
    

    
    def set_auto_focus(enable=True,path=None):
        if path == None:
            print("Favor de indicar camara")
            return
        else:
            if path.set(cv2.CAP_PROP_AUTOFOCUS, 1 if enable else 0):
                print(f"Autoenfoque {'habilitado' if enable else 'deshabilitado'}.")
            else:
                print("La cámara no admite el control de autoenfoque.")
        return

    def set_auto_exposure(enable=True,path=None):
        if path == None:
            print("Favor de indicar camara")
            return
        else:
            if path.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1 if enable else 0):
                print(f"Autoexposición {'habilitada' if enable else 'deshabilitada'}.")
            else:
                print("La cámara no admite el control de autoexposición.")
        return

    def is_focused(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        return laplacian_var > camera_configurations.FOCUS_THRESHOLD

    def is_brightness_ok(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        mean_brightness = np.mean(gray)
        return mean_brightness > camera_configurations.BRIGHTNESS_THRESHOLD

    def adjust_settings(path):
        cameraUtils.set_auto_focus(True,path)
        cameraUtils.set_auto_exposure(True,path)
        time.sleep(2)

    def capture_image(self,filename='captured_image.jpg',path=None):
        if path == None:
            print("Favor de indicar el path de la camara")
            return
        else:
            cameraUtils.adjust_settings(path)
            
            while True:
                ret, frame = path.read()
                if not ret:
                    print("Error al capturar el fotograma.")
                    break

                focused = cameraUtils.is_focused(frame)
                brightness_ok = cameraUtils.is_brightness_ok(frame)

                if focused and brightness_ok:
                    cv2.imwrite(filename, frame)
                    print(f"Imagen capturada y guardada como {filename}")
                    break
                else:
                    status = []
                    if not focused:
                        status.append("enfoque insuficiente")
                    if not brightness_ok:
                        status.append("iluminación insuficiente")
                    print(f"Esperando condiciones óptimas ({', '.join(status)}).")
                    time.sleep(0.5)

    def release(path):
        path.release()
        cv2.destroyAllWindows()
    def release_all_cameras():
        try:
            for path in camera_configurations.CAMERA_PATHS:
                cameraUtils.release(path=path)
                return
        except Exception as e:
            print(f"No se han podido liberar todas las camaras debido a: {e}")
            return
        except:
            print("No se han podido liberar todas las camaras debido a un error no reconocido.")
            return
    
    def rotate_and_save_image(image_path: str, degrees: int = 180):
        """
        Rota una imagen y guarda el resultado sobrescribiendo el archivo original.

        Parámetros:
            image_path (str): Ruta de la imagen original
            degrees (int): Grados de rotación (sólo 180° en este caso)
        """
        try:
            # Leer la imagen
            image = cv2.imread(image_path)
            if image is None:
                raise ValueError("No se pudo leer la imagen")

            # Rotar 180 grados
            rotated = cv2.rotate(image, cv2.ROTATE_180)

            # Sobrescribir la imagen original
            cv2.imwrite(image_path, rotated)

        except Exception as e:
            print(f"Error al rotar la imagen: {e}")
            raise


if __name__ == "__main__":
    camera_capture = None  # Inicializar para manejar excepciones
    try:
        camera_capture = cameraUtils(camera_index=2)
        camera_capture.capture_image()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if camera_capture is not None:
            camera_capture.release()