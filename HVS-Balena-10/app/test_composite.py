"""
Prueba rapida (sin hardware) del motor de composicion del Cambio A usando los
frames de camara REALES de ./tests/images.

Genera UN composite de ejemplo (RAM + LOCK_SHAFT + KOCUP) para calibrar a ojo
config_composite.TEMPLATE_OVERLAY_REGIONS. Solo LEE las imagenes de tests/images
(nunca las borra); el unico directorio que se limpia es ./temporal/images.

Uso:  python3 test_composite.py
Para los escenarios completos de integracion: python3 tests/test_composite_integration.py
"""
import os

from src.configs.configmodels import config_models
from src.configs.configcomposite import config_composite
from src.executors.assembly_composite import assembly_composite


# Frames reales de prueba (NO se borran). Nota: el frontal viene como 'fronal.jpeg'.
IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests", "images")
VIEW_FILES = {
    "frontal":  ["fronal.jpeg", "frontal.jpeg"],
    "backward": ["backward.jpeg"],
    "zenithal": ["zenithal.jpeg"],
}


def _resolve(view):
    for name in VIEW_FILES[view]:
        path = os.path.join(IMAGES_DIR, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(f"No se encontro el frame real para la vista '{view}' en {IMAGES_DIR}")


def main():
    # Inicializa MANDATORY_ASSEMBLY_NAMES (igual que main.py).
    config_models.set_to_default()

    # Requisito A: limpiar SOLO ./temporal/images (no toca ./tests/images).
    assembly_composite.prepare_temporal_images()

    # Coloca los frames reales como cada vista (copia hacia ./temporal/images/<dia>/).
    for view in ("frontal", "backward", "zenithal"):
        assembly_composite.save_view_frame(_resolve(view), view)

    # Escenario "sin vista": un frame cuya vista no se pudo clasificar debe
    # aparecer en el composite como imagen cruda (sin referencia), al final.
    assembly_composite.save_unclassified_frame(_resolve("frontal"))

    failed = ["RAM_ASSEMBLY_AND_DRIVE_BAR", "LOCK_SHAFT_ASSAMBLY", "KOCUP_KOARM_AND_MOLDPLATE"]
    pdf_path = assembly_composite.build_comparison_pdf(failed)

    print("Frames reales usados desde:", IMAGES_DIR)
    print("assembly_to_view:", config_composite.assembly_to_view())
    print("PDF generado:", pdf_path)

    if pdf_path:
        png_path = os.path.join(os.path.dirname(pdf_path), config_composite.COMPOSITE_PNG_NAME)
        import cv2
        img = cv2.imread(png_path)
        print("composite PNG:", png_path, "shape:", None if img is None else img.shape)


if __name__ == "__main__":
    main()
