import pathlib
from src.configs.configmodels import config_models

# Anclamos los paths a la raiz del proyecto (app/) para no depender del cwd.
# __file__ = app/src/configs/configcomposite.py  ->  parents[2] = app/
_APP_ROOT = pathlib.Path(__file__).resolve().parents[2]


class config_composite:
    """
    Configuracion del feature de imagen/PDF comparativo de armado (Cambio A).
    """

    # ---------------------------- Paths ----------------------------------- #
    TEMPLATES_DIR = str(_APP_ROOT / "templates")
    TEMPORAL_IMAGES_DIR = str(_APP_ROOT / "temporal" / "images")

    HEADER_TEMPLATE = "template_header.png"

    # Nombre de archivo del template de "buen armado" por clase obligatoria.
    TEMPLATE_FILE_BY_CLASS = {
        "RAM_ASSEMBLY_AND_DRIVE_BAR": "template_RAM_ASSEMBLY_AND_DRIVE_BAR.png",
        "LOCK_SHAFT_ASSAMBLY":        "template_LOCK_SHAFT_ASSAMBLY.png",
        "KOCUP_KOARM_AND_MOLDPLATE":  "template_KOCUP_KOARM_AND_MOLDPLATE.png",
        "ECCENTRIC_LEVER":            "template_ECCENTRIC_LEVER.png",
        "TUMBLER":                    "template_TUMBLER.png",
    }

    # Region (en pixeles, espacio del template ya normalizado al ancho del header)
    # donde se "vacia" el template y se superpone el frame en vivo.
    # El area vacia esta a la IZQUIERDA; la foto de buen armado ya viene horneada
    # a la derecha del template. CALIBRAR una vez inspeccionando un render real.
    TEMPLATE_OVERLAY_REGIONS = {
        "RAM_ASSEMBLY_AND_DRIVE_BAR": {"x": 60, "y": 330, "w": 860, "h": 910},
        "LOCK_SHAFT_ASSAMBLY":        {"x": 60, "y": 370, "w": 860, "h": 900},
        "KOCUP_KOARM_AND_MOLDPLATE":  {"x": 60, "y": 400, "w": 860, "h": 900},
        "ECCENTRIC_LEVER":            {"x": 60, "y": 360, "w": 860, "h": 900},
        "TUMBLER":                    {"x": 60, "y": 360, "w": 860, "h": 900},
    }

    # Modo de ajuste del frame en vivo dentro de la region (evita deformacion):
    #   "contain" -> muestra el frame COMPLETO, centrado, sin estirar (el resto de
    #                la region queda con el fondo del template). RECOMENDADO.
    #   "cover"   -> llena toda la region sin estirar, recortando lo que sobra.
    #   "stretch" -> deforma el frame para llenar exacto la region (NO recomendado).
    OVERLAY_FIT = "contain"

    # Nombres de archivo de salida (dentro de TEMPORAL_IMAGES_DIR/<dia>/).
    COMPOSITE_PNG_NAME = "composite.png"
    COMPOSITE_PDF_NAME = "composite.pdf"

    # Mapa estatico de respaldo armado->vista, por si MANDATORY_ASSEMBLY_NAMES
    # aun no fue inicializado por config_models.set_to_default().
    _STATIC_ASSEMBLY_TO_VIEW = {
        "RAM_ASSEMBLY_AND_DRIVE_BAR": "backward",
        "LOCK_SHAFT_ASSAMBLY":        "frontal",
        "KOCUP_KOARM_AND_MOLDPLATE":  "frontal",
        "ECCENTRIC_LEVER":            "zenithal",
        "TUMBLER":                    "zenithal",
    }

    @staticmethod
    def assembly_to_view():
        """
        Construye el mapa {clase_armado: vista} invirtiendo
        config_models.MANDATORY_ASSEMBLY_NAMES (fuente de verdad en runtime).
        Si aun no fue inicializado, retorna el mapa estatico de respaldo.
        """
        mapping = {}
        for view, names in (config_models.MANDATORY_ASSEMBLY_NAMES or {}).items():
            for assembly_key in names.values():
                mapping[assembly_key] = view

        if not mapping:
            return dict(config_composite._STATIC_ASSEMBLY_TO_VIEW)
        return mapping
