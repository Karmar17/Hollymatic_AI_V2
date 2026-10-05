"""
Prueba REAL (end-to-end) del flujo de encendido a Zoho Creator.

A DIFERENCIA de test_zoho_encendido.py, aqui NO se mockea la red: se golpean
Grima y Zoho Creator de verdad y se CREA UN REGISTRO REAL con sus imagenes.

Camino de produccion replicado 1:1:
  1. assembly_composite.prepare_temporal_images() limpia ./temporal/images
  2. save_view_frame() deja los frames reales en ./temporal/images/<dia>/<view>.jpeg
  3. ZohoEncendidoProxy().send_encendido() hace:
        login Grima -> getTicket -> crear registro Pendiente -> subir 3 imagenes

El registro se crea con cuatro campos: Hollymatic (Pendiente), ActivarHolly,
link_de_activaci_n y Sucursal. Este ultimo sale de la env var BRANCH; si esta
vacia la prueba aborta antes de crear el registro (ver _check_branch).

Uso:
    cd app
    python3 tests/real_zoho_encendido.py                 # sube las 3 vistas
    python3 tests/real_zoho_encendido.py frontal         # sube solo 'frontal'
"""
import os
import sys

APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

from src.zoho.zoho_proxy import ZohoEncendidoProxy
from src.configs.configzoho import config_zoho
from src.executors.assembly_composite import assembly_composite

IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")


def _place_frames(views):
    assembly_composite.prepare_temporal_images()
    for view in views:
        src = os.path.join(IMAGES_DIR, f"{view}.jpeg")
        dest = assembly_composite.save_view_frame(src, view)
        if not dest or not os.path.exists(dest):
            raise RuntimeError(f"No se pudo colocar el frame real de la vista '{view}'")
        print(f"  frame '{view}' -> {dest}")


def _check_branch():
    """
    El campo 'Sucursal' del registro sale de config.BRANCH (env var BRANCH). Si
    esta vacio, Zoho recibiria un valor nulo/vacio y el registro quedaria sin
    sucursal: mejor abortar antes de crear un registro real inservible.
    """
    branch = config_zoho.HOLLYMATIC_BRANCH_VALUE
    if not branch:
        raise RuntimeError(
            f"La variable de entorno BRANCH esta vacia; el campo "
            f"'{config_zoho.HOLLYMATIC_BRANCH_FIELD}' se enviaria vacio. "
            f"Definela en .env (o en las variables de balena) antes de correr esta prueba.")
    return branch


def main():
    views = sys.argv[1:] or ["frontal", "zenithal", "backward"]

    print("=" * 72)
    print("PRUEBA REAL - Flujo de encendido Zoho Creator (Grima 2 pasos)")
    print(f"  Endpoint Grima : {config_zoho.GRIMA_AUTH_URL}")
    print(f"  Zoho base      : {config_zoho.ZOHO_CREATOR_BASE}")
    print(f"  App / Form     : {config_zoho.ZOHO_APP} / {config_zoho.ZOHO_FORM}")
    print(f"  Vistas a subir : {views}")
    print("  Campos del registro que se creara:")
    print(f"    {config_zoho.HOLLYMATIC_STATUS_FIELD:<22} = {config_zoho.HOLLYMATIC_STATUS_VALUE}")
    print(f"    {config_zoho.HOLLYMATIC_ACTIVATE_FIELD:<22} = {config_zoho.HOLLYMATIC_ACTIVATE_VALUE}")
    print(f"    {config_zoho.HOLLYMATIC_DOMAIN_FIELD:<22} = {config_zoho.HOLLYMATIC_DOMAIN_VALUE}")
    print(f"    {config_zoho.HOLLYMATIC_BRANCH_FIELD:<22} = {config_zoho.HOLLYMATIC_BRANCH_VALUE}")
    print("  *** CREA UN REGISTRO REAL EN ZOHO CREATOR ***")
    print("=" * 72)

    print("\n[1/3] Validando la sucursal configurada (BRANCH)...")
    print(f"  {config_zoho.HOLLYMATIC_BRANCH_FIELD} = {_check_branch()}")

    print("\n[2/3] Colocando frames reales...")
    _place_frames(views)

    print("\n[3/3] Ejecutando send_encendido() contra la red REAL...")
    record_id = ZohoEncendidoProxy().send_encendido()

    print("\n" + "=" * 72)
    if record_id:
        print(f"RESULTADO: OK. Registro creado en Zoho Creator -> ID={record_id}")
        print("Revisa el formulario en Zoho para confirmar estado 'Pendiente', "
              f"sucursal '{config_zoho.HOLLYMATIC_BRANCH_VALUE}' e imagenes.")
    else:
        print("RESULTADO: FALLO. send_encendido() devolvio None. Revisa el log de arriba.")
        sys.exit(1)


if __name__ == "__main__":
    main()
