import os
from ultralytics import YOLO
from typing import Optional, List, Tuple, Any
from src.configs.configmodels import config_models
from src.utils.camerautils import cameraUtils

class inferencer:

    def classify_view(image_path: str) -> Optional[str]:
            """
            Clasifica la vista de la imagen (frontal, zenithal, backward) y rota 180° si es la cámara tracera.

            Parámetros:
                image_path (str): Path de la imagen a clasificar

            Retorna:
                str: Vista predicha ('frontal', 'zenithal', 'backward') o None si falla
            """
            if not config_models.CLASSIFICATION_MODEL:
                print("Error: Modelo de clasificación no cargado")
                return None

            if not os.path.exists(image_path):
                print(f"Error: Imagen no encontrada en {image_path}")
                return None

            try:
                # 1. Clasificar la imagen
                results = config_models.CLASSIFICATION_MODEL.predict(image_path, imgsz=640)
                result = results[0]

                top_class_idx = result.probs.top1
                top_class_name = config_models.CLASSIFICATION_MODEL.names[top_class_idx]
                confidence = result.probs.top1conf.item()
                if top_class_name == 'tracera':
                    top_class_name = 'backward'
                if top_class_name == 'superior':
                    top_class_name = 'zenithal'

                print(f"Clasificación: Cámara {top_class_name} (Confianza: {confidence:.2%})")

                # 2. Rotar la imagen si es la cámara tracera
                if top_class_name == 'backward':
                    cameraUtils.rotate_and_save_image(image_path, degrees=180)
                    print("Imagen rotada 180° (cámara tracera)")

                return top_class_name

            except Exception as e:
                print(f"Error en clasificación: {e}")
                return None
    
    def inference(image_path: str, view: str) -> Optional[Tuple[List, Any]]:
        if view == 'backward':
            print("segment_image = Vista Backward - Ejecutando DETECCIÓN")
            models = config_models.BACKWARD_MODEL_PATH
            is_detection = True
        if view == 'frontal':
            print(f"segment_image = Vista {view} - Ejecutando SEGMENTACIÓN")
            models = config_models.FRONTAL_MODEL_PATH
            is_detection = False
        if view == "zenithal":
            print(f"segment_image = Vista {view} - Ejecutando SEGMENTACIÓN")
            models = config_models.ZENITHAL_MODEL_PATHS

        for model in models:
            try:
                model = YOLO(model)
            except Exception as e:
                print(f"No se ha podido cargar el modelo de yolo debido a: {e}")
                return
            except: 
                print("No se ha podido carcar el modelo de yolo debido a un error no identificado")
                return

            try:
                try:
                    results = model(image_path)
                except Exception as e:
                    print(f"No se ha podido cargar el modelo debido a: {e}")
                    return
                except:
                    print("No se ha podido cargar el modelo debido a un error no identificado")
                    return
                
                try:
                    results = results[0]
                except Exception as e:
                    print(f"No se han podido obtener los resultados de la infencia debido a: {e}")
                    return
                except:
                    print("No se han podido obtener los resultados de la infencia debido a un error inersperado")
                    return
            except Exception as e:
                print(f"El proceso de inferencia ha fallado debido a: {e}")
                return
            except:
                print("El proceso de inferencia a fallado debido a un error inesperado")
                return

            inferencer.__manage_results(result=results,model=model,view=view)

        return

            
        

    def __manage_results(result,model,view):
            # Itera sobre cada detección en los resultados.
        for box in result.boxes:
            # Extrae las coordenadas del bounding box.
            coordinates = [int(coord) for coord in box.xyxy[0]]
            
            # Obtiene la confianza de la detección.
            confidence = box.conf[0]
            
            # Obtiene el ID de la clase y su nombre.
            class_id = int(box.cls[0])
            class_name = model.names[class_id]
            

            # Imprime la información en la consola.
            print(f"Clase: {class_name}, Confianza: {confidence:.2f}, Coordenadas:{coordinates}")

            dfresults = {
                'view': view,
                'class_name' : class_name,
                'class_id' : class_id,
                'coordinates': coordinates,
            }

            if(confidence > config_models.MIN_CONFIDENCE):
                config_models.RESULTS.append(dfresults)
            else:
                pass

        return

 


