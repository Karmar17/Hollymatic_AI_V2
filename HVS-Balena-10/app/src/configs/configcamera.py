import cv2
import datetime
from src.configs.configs import config

class camera_configurations:

    CAMERAS = {}
    CAMERA_PATHS = config.CAMERA_PATHS

    FOCUS_THRESHOLD = config.FOCUS_THRESHOLD
    BRIGHTNESS_THRESHOLD = config.BRIGHTNESS_THRESHOLD

    FILENAME = datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S')+".jpeg"

    def set(camera_path):

        cap = cv2.VideoCapture(camera_path)
        if not cap.isOpened():
            print(f"Error: No se pudo abrir la cámara en {camera_path}")
            return None

        try:
            # Configurar cámara
            cap.set(cv2.CAP_PROP_FOCUS, 40)
            cap.set(cv2.CAP_PROP_FPS, 60)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        except:
            print("Error al configurar la camara")
        return cap
