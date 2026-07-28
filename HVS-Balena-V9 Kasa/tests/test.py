import cv2
import numpy as np

# Cargar imágenes
fondo = cv2.imread('./images/1.png')
frontal = cv2.imread('./images/2.png')

# Obtener dimensiones de la imagen frontal
alto, ancho, canales = frontal.shape

# Definir la posición de inicio (ej. esquina superior izquierda, y = 50, x = 50)
y, x = 50, 50

# Extraer la región de interés (ROI) del fondo
roi = fondo[y:y+alto, x:x+alto]

# Sobrescribir la ROI con la imagen frontal
fondo[y:y+alto, x:x+alto] = frontal

cv2.imshow('Imagen Superpuesta', fondo)
cv2.waitKey(0)
cv2.destroyAllWindows()
