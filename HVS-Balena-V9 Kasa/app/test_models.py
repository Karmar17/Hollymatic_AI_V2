import cv2
from ultralytics import YOLO

# --- Configuración ---
# Carga tu modelo YOLO. Puede ser un modelo pre-entrenado ('yolov8n.pt')
# o uno que tú hayas entrenado ('/ruta/a/tu/best.pt').
try:
    model = YOLO('/home/sergio/Documentos/Refactor-Hollymatic/test-deploy/HVS-Balena/app/models/zenithal_models/zenithal_assembly_model.pt')  # <-- CAMBIA AQUÍ por la ruta a tu modelo
except Exception as e:
    print(f"Error al cargar el modelo: {e}")
    exit()

# Ruta de la imagen que quieres analizar.
image_path = '/home/sergio/Documentos/Jorge Rosas/armado holly/721.jpg'  # <-- CAMBIA AQUÍ por la ruta de tu imagen

# --- Inferencia ---
try:
    # Realiza la inferencia en la imagen.
    results = model(image_path)

    # El resultado 'results' es una lista de objetos.
    # Para una sola imagen, trabajaremos con el primer elemento.
    result = results[0]

    # --- Procesamiento de Resultados ---
    # Carga la imagen original para visualizar los resultados.
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(f"No se pudo encontrar o leer la imagen en: {image_path}")

    # Itera sobre cada detección en los resultados.
    for box in result.boxes:
        # Extrae las coordenadas del bounding box.
        x1, y1, x2, y2 = [int(coord) for coord in box.xyxy[0]]
        
        # Obtiene la confianza de la detección.
        confidence = box.conf[0]
        
        # Obtiene el ID de la clase y su nombre.
        class_id = int(box.cls[0])
        class_name = model.names[class_id]
        
        # Dibuja el bounding box en la imagen.
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Prepara el texto (clase + confianza).
        label = f'{class_name} {confidence:.2f}'
        
        # Dibuja el fondo para el texto.
        cv2.putText(img, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        # Imprime la información en la consola.
        print(f"Clase: {class_name}, Confianza: {confidence:.2f}, Coordenadas: [{x1}, {y1}, {x2}, {y2}]")


    # --- Visualización ---
    # Muestra la imagen con las detecciones.
    cv2.imshow('Inferencia YOLO', img)

    # Espera a que el usuario presione una tecla para cerrar la ventana.
    cv2.waitKey(0)

    # Cierra todas las ventanas de OpenCV.
    cv2.destroyAllWindows()

except Exception as e:
    print(f"Ocurrió un error durante la inferencia: {e}")
