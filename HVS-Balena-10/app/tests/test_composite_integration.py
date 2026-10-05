"""
Tests de integracion del Cambio A (PDF comparativo de armado) usando frames de
camara REALES de ./tests/images.

Por cada escenario:
  1. Limpia ./temporal/images (Requisito A).
  2. Coloca los frames reales como las vistas correspondientes (Requisito B).
  3. Compone el PDF comparativo (Requisito C) con assembly_composite.
  4. Copia el PNG y el PDF resultantes a ./tests/output/<escenario>/ para que se
     puedan ABRIR y VALIDAR MANUALMENTE.
  5. Verifica dimensiones, numero de secciones y que el PDF tenga UNA sola pagina.

Uso (validacion manual):
    python3 tests/test_composite_integration.py
    # luego revisar ./tests/output/<escenario>/composite.png|pdf

Tambien es compatible con pytest:
    pytest tests/test_composite_integration.py -s
"""
import os
import re
import sys
import shutil
import datetime

import cv2

# Permite ejecutar el archivo directamente (python3 tests/...) y que `src` sea importable.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from src.configs.configmodels import config_models
from src.configs.configcomposite import config_composite
from src.executors.assembly_composite import assembly_composite


IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

# Nombre(s) de archivo real por vista. Se acepta 'frontal.jpeg' o el typo 'fronal.jpeg'.
VIEW_FILES = {
    "frontal":  ["frontal.jpeg", "fronal.jpeg"],
    "backward": ["backward.jpeg"],
    "zenithal": ["zenithal.jpeg"],
}


def _resolve_view_file(view):
    for name in VIEW_FILES[view]:
        path = os.path.join(IMAGES_DIR, name)
        if os.path.exists(path):
            return path
    raise FileNotFoundError(
        f"No se encontro el frame real para la vista '{view}' en {IMAGES_DIR} "
        f"(se buscaron: {VIEW_FILES[view]})")


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _today_dir():
    return os.path.join(
        config_composite.TEMPORAL_IMAGES_DIR,
        datetime.datetime.now().strftime("%Y-%m-%d"))


def _header_height():
    header = cv2.imread(os.path.join(config_composite.TEMPLATES_DIR,
                                     config_composite.HEADER_TEMPLATE))
    return header.shape[0], header.shape[1]  # (h, w)


def _section_height(target_width):
    # Todos los templates de clase son del mismo alto; tomamos uno de referencia.
    sample = cv2.imread(os.path.join(
        config_composite.TEMPLATES_DIR,
        config_composite.TEMPLATE_FILE_BY_CLASS["RAM_ASSEMBLY_AND_DRIVE_BAR"]))
    h, w = sample.shape[:2]
    if w != target_width:
        h = int(round(h * (target_width / float(w))))
    return h


def _pdf_page_count(pdf_path):
    # Cuenta objetos /Type /Page (excluye /Type /Pages gracias al \b).
    with open(pdf_path, "rb") as f:
        data = f.read()
    return len(re.findall(rb"/Type\s*/Page\b", data))


def _place_frames(provided_views):
    """Copia los frames reales de las vistas indicadas a ./temporal/images/<dia>/."""
    for view in provided_views:
        src = _resolve_view_file(view)
        dest = assembly_composite.save_view_frame(src, view)
        assert dest and os.path.exists(dest), f"No se pudo colocar el frame de la vista {view}"


def run_scenario(name, failed, provided_views):
    """
    Ejecuta un escenario completo y deja los artefactos en ./tests/output/<name>/.
    Retorna un dict con la informacion del resultado.
    """
    config_models.set_to_default()  # inicializa MANDATORY_ASSEMBLY_NAMES
    assembly_composite.prepare_temporal_images()
    _place_frames(provided_views)

    pdf_path = assembly_composite.build_comparison_pdf(failed)

    out_dir = os.path.join(OUTPUT_DIR, name)
    os.makedirs(out_dir, exist_ok=True)

    info = {"name": name, "failed": failed, "provided": provided_views, "pdf": None,
            "png_shape": None, "pages": None, "sections": 0}

    if pdf_path is None:
        return info

    png_src = os.path.join(_today_dir(), config_composite.COMPOSITE_PNG_NAME)
    pdf_dst = os.path.join(out_dir, "composite.pdf")
    png_dst = os.path.join(out_dir, "composite.png")
    shutil.copyfile(pdf_path, pdf_dst)
    if os.path.exists(png_src):
        shutil.copyfile(png_src, png_dst)

    img = cv2.imread(png_dst) if os.path.exists(png_dst) else None
    _, target_w = _header_height()
    sec_h = _section_height(target_w)
    head_h, _ = _header_height()

    info["pdf"] = pdf_dst
    info["png_shape"] = None if img is None else img.shape
    info["pages"] = _pdf_page_count(pdf_dst)
    if img is not None:
        info["sections"] = round((img.shape[0] - head_h) / float(sec_h))
    return info


# --------------------------------------------------------------------------- #
#  Escenarios
# --------------------------------------------------------------------------- #
# expected = numero de secciones esperadas en el composite.
SCENARIOS = {
    "example_three_classes": {
        "title": "Ejemplo 3 clases (RAM+LOCK_SHAFT+KOCUP)",
        "failed": ["RAM_ASSEMBLY_AND_DRIVE_BAR", "LOCK_SHAFT_ASSAMBLY", "KOCUP_KOARM_AND_MOLDPLATE"],
        "provided": ["frontal", "backward", "zenithal"],
        "expected": 3,
    },
    "all_five_classes": {
        "title": "Las 5 clases",
        "failed": ["RAM_ASSEMBLY_AND_DRIVE_BAR", "LOCK_SHAFT_ASSAMBLY",
                   "KOCUP_KOARM_AND_MOLDPLATE", "ECCENTRIC_LEVER", "TUMBLER"],
        "provided": ["frontal", "backward", "zenithal"],
        "expected": 5,
    },
    "single_class": {
        "title": "Una sola clase (RAM / backward)",
        "failed": ["RAM_ASSEMBLY_AND_DRIVE_BAR"],
        "provided": ["backward"],
        "expected": 1,
    },
    "zenithal_pair": {
        "title": "Par zenithal (ECCENTRIC+TUMBLER, mismo frame)",
        "failed": ["ECCENTRIC_LEVER", "TUMBLER"],
        "provided": ["zenithal"],
        "expected": 2,
    },
    "missing_view": {
        "title": "Vista faltante (RAM omitido, solo frontal provisto)",
        "failed": ["RAM_ASSEMBLY_AND_DRIVE_BAR", "LOCK_SHAFT_ASSAMBLY"],
        "provided": ["frontal"],
        "expected": 1,
    },
}


def _assert_scenario(key):
    """Ejecuta un escenario y verifica PDF, ancho, # secciones y # paginas."""
    spec = SCENARIOS[key]
    info = run_scenario(key, spec["failed"], spec["provided"])
    _, head_w = _header_height()
    assert info["pdf"] and os.path.exists(info["pdf"]), f"{key}: no se genero el PDF"
    assert info["png_shape"][1] == head_w, f"{key}: ancho {info['png_shape'][1]} != {head_w}"
    assert info["sections"] == spec["expected"], \
        f"{key}: secciones {info['sections']} != {spec['expected']}"
    assert info["pages"] == 1, f"{key}: PDF con {info['pages']} paginas (deberia ser 1)"
    return info


# Funciones de test (compatibles con pytest; no retornan valor).
def test_example_three_classes():
    """Ejemplo de la propuesta: RAM + LOCK_SHAFT + KOCUP."""
    _assert_scenario("example_three_classes")


def test_all_five_classes():
    """Las 5 clases mal armadas a la vez."""
    _assert_scenario("all_five_classes")


def test_single_class():
    """Una sola clase mal armada."""
    _assert_scenario("single_class")


def test_zenithal_pair_same_frame():
    """ECCENTRIC_LEVER + TUMBLER (ambas zenithal): mismo frame en dos secciones."""
    _assert_scenario("zenithal_pair")


def test_missing_view_is_skipped():
    """Falta el frame de una vista: esa seccion se omite con gracia (log critical)."""
    _assert_scenario("missing_view")


def test_no_frames_returns_none():
    """Sin ningun frame disponible no se genera PDF (retorna None)."""
    config_models.set_to_default()
    assembly_composite.prepare_temporal_images()
    pdf_path = assembly_composite.build_comparison_pdf(["RAM_ASSEMBLY_AND_DRIVE_BAR"])
    assert pdf_path is None


# --------------------------------------------------------------------------- #
#  Runner manual
# --------------------------------------------------------------------------- #
def main():
    print("=" * 70)
    print("TESTS DE INTEGRACION - PDF comparativo (Cambio A)")
    print(f"Frames reales: {IMAGES_DIR}")
    print(f"Salida para validacion manual: {OUTPUT_DIR}")
    print("=" * 70)

    failures = 0
    for key, spec in SCENARIOS.items():
        try:
            info = _assert_scenario(key)
            print(f"\n[OK] {spec['title']}")
            print(f"     secciones={info['sections']}  paginas_pdf={info['pages']}  "
                  f"png={info['png_shape']}")
            print(f"     abrir -> {info['pdf']}")
        except AssertionError as e:
            failures += 1
            print(f"\n[FALLA] {spec['title']}: {e}")

    try:
        test_no_frames_returns_none()
        print("\n[OK] Sin frames -> no se genera PDF (None)")
    except AssertionError as e:
        failures += 1
        print(f"\n[FALLA] Sin frames: {e}")

    print("\n" + "=" * 70)
    if failures:
        print(f"RESULTADO: {failures} escenario(s) con fallas.")
        sys.exit(1)
    print("RESULTADO: todos los escenarios OK. Revisa los composites en tests/output/.")


if __name__ == "__main__":
    main()
