import os
from ultralytics import YOLO
from src.configs.configmodels import config_models
from src.configs.configlogger import logger_config

class model_loader:
    def __init__(self):
            """
                Inicializa la clase model_loader.
            """

            self.logger = logger_config.main_production_logger
            


        
    def clasification(self,path):
        """
        
        
        """

        try:
            config_models.CLASSIFICATION_MODEL = self.model(path,config_models.CLASSIFICATION_MODEL)
            self.logger.info(f"Modelo de clasificación cargado: {path}")

        except Exception as e:

            config_models.MODEL_ERRORS.append(f"CLASIFICACIÓN: {str(e)}")
            config_models.CLASSIFICATION_MODEL = None
        
        return
    
    def segmentation(self,loaded_segmentation_models):
        segmentation = None
        self.logger.info("Se inicia iteracion por cada una de los planos (views) disponibles")
        for view in config_models.CAMERA_LOCATIONS:

            try:
                    paths = config_models.MODEL_PATHS[view]

                    if isinstance(paths, str):
                        paths = [paths]  # convertir a lista si es un solo path

                    for path in paths:
                        self.logger.info(f"Cargando los modelos de validacion de correcto armado: {path}")
                        segmentation = self.model(path,segmentation)
                        config_models.LOADED_MODELS.append(segmentation)

                        self.logger.info(f"Modelo {view} cargado: {path}")


                    self.logger.info(f"en {view} se cargarón los modelos {path}")
                    config_models.SEGMENTATION_MODELS[view] = config_models.LOADED_MODELS
                    loaded_segmentation_models += 1

            except Exception as e:
                config_models.MODEL_ERRORS.append(f"{view.upper()}: {str(e)}")
                config_models.SEGMENTATION_MODELS[view] = None

            except:
                self.logger.error("Error al cargar los modelos de segmentación")
                

        return loaded_segmentation_models

    def model(self,path,model):

        if not os.path.exists(path):
            raise FileNotFoundError(f"Archivo no encontrado: {path}")
        try:
            model = YOLO(path)
        except Exception as e:
            self.logger.error(f"No se pudo cargar el modelo debido a: {e}")
        self.logger.info(f"Modelo cargado: {path}")

        return model
    
    def load_models(self):
        """
        Carga todos los modelos necesarios.

        Raises:
            ValueError: Si no se puede cargar el modelo de clasificación o 
                        ninguno de los modelos de segmentación.
            FileNotFoundError: Si algún archivo de modelo no existe.
        """
        #self.segmentation_models = {}
        loaded_segmentation_models = 0

        # Cargar modelo de clasificación
        try:
            self.logger.info("Cargando modelos de clasificacion")
            path = config_models.MODEL_PATHS['classification']
            self.clasification(path)

        except:
            self.logger.error("Error al cargar el modelo de clasificación")

        # Cargar modelos de segmentación
        try:
            self.logger.info("Cargando modelos de inferencia de piezas")
            loaded_segmentation_models = self.segmentation(loaded_segmentation_models)
        except Exception as e:
            self.logger.critical(f"Se ha producido un error cargando los modelos de inferencia en piezas debido a: {e}")
        except:
            self.logger.critical("Se ha producido un error cargando los modelos de inferencia en piezas debido a un error no reconocido")

        # Verificar si se cargó al menos un modelo de clasificación y segmentación
        if not config_models.CLASSIFICATION_MODEL:
            self.logger.critical("No se ha podido cargar el modelo de clasificación")
            config_models.MODEL_ERRORS.insert(0, "No se pudo cargar el modelo de clasificación (requerido)")

        if not config_models.CLASSIFICATION_MODEL or loaded_segmentation_models < 3:
            print(loaded_segmentation_models)
            error_msg = "Errores al cargar modelos:\n  " + "\n  ".join(config_models.MODEL_ERRORS)
            raise ValueError(error_msg)
        self.logger.info("Modelos cargados exitosamente")