
import time
import asyncio
from typing import Dict, Optional
from src.configs.configs import config
from src.configs.configmodels import config_models
from src.configs.configmikasa import config_mikasa
from src.configs.configlogger import logger_config
from src.inference.modelsloaders import model_loader
from src.inference.inference_yolo import inferencer
from src.google.gchat import gchat
from src.utils.bboxUtils import bbox_utils
from src.executors.image import imager
from src.executors.assembly_composite import assembly_composite
from src.google.gchat import gchat


class HollyVisionSystem:
    """
    Sistema de visión completo para el proyecto Holly que maneja:
    - Verificación de cámaras conectadas
    - Captura de imágenes
    - Clasificación de vistas (frontal, zenithal, backward)
    - Segmentación específica por vista

    Atributos:
    ----------
    classification_model : YOLO
        Modelo para clasificar la vista de la imagen
    segmentation_models : dict
        Diccionario con modelos de segmentación por vista
    """

    def __init__(self):
        """
        Inicializa el sistema cargando los modelos necesarios.
        """
        loader = model_loader()
        loader.load_models()
        self.logger = logger_config.main_production_logger
        self.imager = imager()
        

    def full_processing(self, camera_path: str) -> Optional[Dict]:
        """
        Ejecuta el flujo completo de procesamiento:
        1. Captura imagen
        2. Clasifica vista
        3. Segmenta según vista

        Parámetros:
            camera_path (str): Path de la cámara a usar

        Retorna:
            Dict: Diccionario con todos los resultados o None si falla
        """

        # Paso 1: Capturar imagen
        try:
            self.logger.info("Iniciando captura de imagenes")
            img_path = self.imager.capture_image(camera_path,"./captures")
            if not img_path:
                return None
        except Exception as e:
            self.logger.critical(f"No se ha podido tomar la fotografia debido a: {e}")
        except:
            self.logger.critical("No se ha podido tomar la fotografia debido a un error no reconocido")

        # Paso 2: Clasificar vista
        try:
            self.logger.info("Iniciando identificacion al plano correspondiente a la imagen")
            view = inferencer.classify_view(img_path)
            if not view:
                self.logger.info("No se detecto la vista del frame; se guarda como 'sin referencia'")
                assembly_composite.save_unclassified_frame(img_path)
                return  # sin vista no se puede inferir; el frame igual ira al composite
            assembly_composite.save_view_frame(img_path, view)

        except Exception as e:
            self.logger.critical(f"No se ha podido identificar a que plano corresponde la camara debido a: {e}")
        except:
            self.logger.critical("No se ha podido identificar a que plano corresponde la camara debido a un error no reconocido")

        # Paso 3: Segmentar según vista 
        try:
            self.logger.info(f"Se ha iniciado el proceso de inferencia de imagan {img_path}")      
            #inferencer.inference(test_image, view)
            inferencer.inference(img_path, view)
        except Exception as e:
            self.logger.critical(f"No se ha podido generar la inferencia de las imagenes de hollymatic debido a: {e}")
        except:
            self.logger.critical("No se ha podido generar la inferencia de las imagenes de hollymatic debido a un error no reconocido")
        return

    def capture_and_classify(self, camera_path: str) -> Optional[str]:
        """
        Para el flujo de encendido/calibracion: captura una imagen de la camara,
        clasifica su vista y la guarda como frame de esa vista. No segmenta.
        Retorna la vista clasificada ('frontal'/'zenithal'/'backward') o None.
        """
        # Paso 1: Capturar imagen
        try:
            self.logger.info(f"Iniciando captura de imagen de {camera_path}")
            img_path = self.imager.capture_image(camera_path, "./captures")
            if not img_path:
                return None
        except Exception as e:
            self.logger.critical(f"No se ha podido tomar la fotografia debido a: {e}")
            return None

        # Paso 2: Clasificar vista y guardar frame por vista
        try:
            self.logger.info("Iniciando identificacion del plano correspondiente a la imagen")
            view = inferencer.classify_view(img_path)
            if not view:
                self.logger.info("No se detecto la vista del frame; se guarda como 'sin referencia'")
                assembly_composite.save_unclassified_frame(img_path)
                return None
            assembly_composite.save_view_frame(img_path, view)
            return view
        except Exception as e:
            self.logger.critical(f"No se ha podido clasificar la vista de la camara debido a: {e}")
            return None

    def correct_assambly(self, results):
        try:
            self.logger.info("Iniciando proceso de obtencion de JSON de correcto armado")
            correct_assembly_json = config_models.correct_assembly_json()
        except Exception as e:
            self.logger.critical(f"No se ha podido obtener el JSON que indica los planos de correcto armado debido a: {e}")
        except:
            self.logger.critical("No se ha podido obtener el JSON que indica los planos de correcto armado debido a un error no reconocido")

        
        for result in results:
            print(result)
            view = result.get('view')
            class_name = result.get('class_name')
            bbox = result.get('coordinates')

            for correct_assembly in correct_assembly_json:
                    jsonview = correct_assembly.get('view')
                    if view == jsonview:

                            self.logger.info("Se ha iniciado el proceso de obtencion de clases de correcto armado")
                            correct_classes_names = correct_assembly.get('correct_classes_names')
                            for correct_class_names in correct_classes_names:
                                    print(f" correct_class_names ANTES split: {correct_class_names}")
                                    correct_class_names = correct_class_names.split(",")
                                    print(f"correct_class_names DESPUÉS split: {correct_class_names}")
                                    for correct_class_name in correct_class_names:
                                        print(f"correct_class_name: {correct_class_name}")
                                        correct_class_name = correct_class_name.replace(" ","")
                                        print(f"{class_name} == {correct_class_name}")
                                        if class_name == correct_class_name:
                                            self.logger.info("Se ha iniciado la validacion de los las clases obligatorias de correcto armado")
                                            mandatory_assembly = self.__assembly_is_correct(correct_assembly,class_name)
                                            self.logger.info(f"Se ha indicado que se ha detectado correctamente {mandatory_assembly}")
                                            config_models.MANDATORY_ASSEMBLY[mandatory_assembly] = True
                                    if view == 'backward':
                                        for lock_pin in config_models.LOCK_PIN_CLASSES:
                                            if class_name == lock_pin:
                                                    self.logger.info("Validando daños en lockpin")
                                                    bbox_aspect_ratio = bbox_utils.bbox_lenght(bbox)
                                                    print(bbox_aspect_ratio)
                                                    if bbox_aspect_ratio > config_models.BBOX_MAX_ASPECT_RATIO:
                                                            self.logger.info("Se ha detectado que el lock pin se encuentra roto")
                                                            gchat.send_advice("Se ha detectado que la pieza indicadora para el ajuste de la carne se encuentra rota.")
                                                            print(f"bbox_aspect_ratio:{bbox_aspect_ratio}")
                                                        
                                    
        print(config_models.MANDATORY_ASSEMBLY)


         
    def __assembly_is_correct(self,correct_assembly,class_name):

        try:
            mandatory_assembly_names = correct_assembly.get('mandatory_assembly_names')

        except Exception as e:
            self.logger.critical(f"No se han podido obtener los assambly obligatorios debido a: {e}")
        except:
            self.logger.critical(f"No se han podido obtener los assambly obligatorios debido a un error no reconocido")


        try:
            correct_class_name = mandatory_assembly_names.get(class_name)

        except Exception as e:
            self.logger.critical(f"No se han podido obtener los nombres de los assamblies debido a: {e}")
        except:
            self.logger.critical(f"No se han podido obtener los nombres de los assamblies debido a un error no reconocido")
        
        return correct_class_name
    
    async def hollymatic_shut_down(self):
        print("Apagando Hollymatic")
        try:
            await config_mikasa.CONTROLLER.update_plugs(False)

        except Exception as e:
             print(f"No se ha podido desenergetizar la hollymatic debido a: {e}")
        except:
             print("No se ha podido desenergetizar la hollymatic debido a un error no reconocido.")

    
    async def hollymatic_turn_on(self):
        try:
            await config_mikasa.CONTROLLER.update_plugs(True)

        except Exception as e:
             self.logger.critical(f"No se ha podido energetizar la hollymatic debido a: {e}")
        except:
             self.logger.critical("No se ha podido energetizar la hollymatic debido a un error no reconocido.")

    async def hollymatic_calibrate(self):
        print("Calibrando Hollymatic")
        try:
            await config_mikasa.CONTROLLER.update_plugs(True)
            time.sleep(45)


        except Exception as e:
             self.logger.critical(f"No se ha podido energetizar la hollymatic debido a: {e}")
        except:
             self.logger.critical("No se ha podido energetizar la hollymatic debido a un error no reconocido.")
        try:
             await config_mikasa.CONTROLLER.update_plugs(False)

        except Exception as e:
             self.logger.critical(f"No se ha podido desenergetizar la hollymatic debido a: {e}")
        except:
             self.logger.critical("No se ha podido desenergetizar la hollymatic debido a un error no reconocido.")
        
    async def discover_kp200(self):
        try:
            await config_mikasa.CONTROLLER.discover_device()

        except Exception as e:
            self.logger.critical(f"No se encontro KP200 debido a: {e}")
        except:
            self.logger.critical("No se encontro KP200 debido a un error no reconocido.")

                              


                        
                        
                        
                        
                        
