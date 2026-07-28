"""
Tests del flujo de encendido a Zoho Creator (autorizacion de 2 pasos Grima -> Zoho)
usando los frames REALES de ./tests/images (frontal.jpeg, zenithal.jpeg, backward.jpeg).

El flujo bajo prueba (src/zoho/zoho_proxy.py -> ZohoEncendidoProxy.send_encendido):
  1. Login Grima            -> token_grima
  2. getTicket (Bearer)     -> token_zoho
  3. Crea registro Pendiente en el formulario -> record_id
  4. Sube cada imagen clasificada al campo correspondiente del registro.

La RED se mockea (no se golpea Grima/Zoho reales), pero:
  - Las imagenes se colocan con el flujo REAL: assembly_composite.save_view_frame()
    deja los frames en ./temporal/images/<dia>/<view>.jpeg y el proxy los lee via
    assembly_composite.view_frame_path(). Asi se ejercita el camino de produccion.
  - Se verifica: two-step auth, URLs, mapeo vista->campo (frontal->Frontal,
    zenithal->Cenital, backward->Tracera), que los BYTES subidos == la imagen real,
    reintentos ante error transitorio, cache de tokens y el caso de vista faltante.

Uso:
    pytest tests/test_zoho_encendido.py -s
    # o directamente:
    python3 tests/test_zoho_encendido.py
"""
import os
import sys

# Permite ejecutar el archivo directamente y que `src` sea importable.
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_ROOT not in sys.path:
    sys.path.insert(0, APP_ROOT)

import src.zoho.zoho_proxy as zoho_proxy
from src.zoho.zoho_proxy import ZohoEncendidoProxy
from src.configs.configzoho import config_zoho
from src.executors.assembly_composite import assembly_composite


IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "images")

# Sin espera real entre reintentos durante los tests.
config_zoho.NET_BACKOFF_BASE = 0

# Bytes reales de cada imagen de prueba, para comparar contra lo que se "sube".
REAL_IMAGE_BYTES = {
    view: open(os.path.join(IMAGES_DIR, f"{view}.jpeg"), "rb").read()
    for view in ("frontal", "zenithal", "backward")
}


# --------------------------------------------------------------------------- #
#  Transporte de red simulado
# --------------------------------------------------------------------------- #
class _FakeResp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeZohoTransport:
    """
    Reemplaza requests.request. Registra cada llamada y responde segun la URL,
    validando cabeceras/cuerpo del flujo. `transient_500` fuerza N respuestas 500
    iniciales del login Grima para ejercitar los reintentos.
    """
    def __init__(self, transient_500=0):
        self.calls = []              # (method, url, auth_header)
        self.uploaded = {}           # field_link_name -> bytes subidos
        self._grima_500_left = transient_500

    def __call__(self, method, url, **kwargs):
        headers = kwargs.get("headers", {}) or {}
        self.calls.append((method, url, headers.get("Authorization")))

        if "authRestApi" in url:
            body = kwargs.get("json", {})
            assert body.get("username") == config_zoho.GRIMA_USERNAME
            assert "password" in body
            if self._grima_500_left > 0:
                self._grima_500_left -= 1
                return _FakeResp(500, text="server error")
            return _FakeResp(200, {"success": True, "data": {"token": "GRIMA_TOK"}})

        if "getTicket" in url:
            assert headers.get("Authorization") == "Bearer GRIMA_TOK"
            body = kwargs.get("json", {})
            assert body.get("account") == config_zoho.ZOHO_ACCOUNT
            assert body.get("application") == config_zoho.ZOHO_APPLICATION
            return _FakeResp(200, {"success": True, "data": {"token": "ZOHO_TOK"}})

        if url.endswith(f"/form/{config_zoho.ZOHO_FORM}"):
            assert headers.get("Authorization") == "Zoho-oauthtoken ZOHO_TOK"
            body = kwargs.get("json", {})
            # Debe crearse UN SOLO registro con los tres campos juntos. Si se
            # crean varios registros (o falta algun campo), Zoho aplicaria el
            # default "Aprobado" al campo Hollymatic ausente -> regresion.
            assert len(body["data"]) == 1, (
                f"se esperaba 1 registro, se enviaron {len(body['data'])}: {body['data']}")
            record = body["data"][0]
            assert record[config_zoho.HOLLYMATIC_STATUS_FIELD] == config_zoho.HOLLYMATIC_STATUS_VALUE
            assert record[config_zoho.HOLLYMATIC_ACTIVATE_FIELD] == config_zoho.HOLLYMATIC_ACTIVATE_VALUE
            assert record[config_zoho.HOLLYMATIC_DOMAIN_FIELD] == config_zoho.HOLLYMATIC_DOMAIN_VALUE
            assert record[config_zoho.HOLLYMATIC_BRANCH_FIELD] == config_zoho.HOLLYMATIC_BRANCH_VALUE
            # Shape REAL del add-records v2.1 (verificado contra el endpoint):
            return _FakeResp(200, {
                "result": [{"code": 3000, "data": {"ID": "REC123"},
                            "message": "Data Added Successfully"}],
                "code": 3000,
            })

        if "/upload" in url:
            assert headers.get("Authorization") == "Zoho-oauthtoken ZOHO_TOK"
            # .../report/<report>/<recordID>/<field>/upload
            field = url.split("/REC123/")[1].split("/upload")[0]
            # Verifica el report link-name real en la URL de subida.
            assert f"/report/{config_zoho.ZOHO_REPORT}/" in url, url
            fname, fh = kwargs["files"]["file"][0], kwargs["files"]["file"][1]
            self.uploaded[field] = fh.read()
            return _FakeResp(200, {"code": 3000, "data": {
                "filename": fname, "message": "File Uploaded Successfully"}})

        raise AssertionError(f"URL inesperada: {url}")


# --------------------------------------------------------------------------- #
#  Helpers
# --------------------------------------------------------------------------- #
def _place_frames(views):
    """Coloca los frames reales de `views` con el flujo real (save_view_frame)."""
    assembly_composite.prepare_temporal_images()
    for view in views:
        src = os.path.join(IMAGES_DIR, f"{view}.jpeg")
        dest = assembly_composite.save_view_frame(src, view)
        assert dest and os.path.exists(dest), f"No se pudo colocar el frame '{view}'"


def _run(views, transient_500=0):
    """Prepara frames, instala el transporte fake y ejecuta send_encendido()."""
    _place_frames(views)
    fake = FakeZohoTransport(transient_500=transient_500)
    original = zoho_proxy.requests.request
    zoho_proxy.requests.request = fake
    try:
        proxy = ZohoEncendidoProxy()
        record_id = proxy.send_encendido()
        return proxy, fake, record_id
    finally:
        zoho_proxy.requests.request = original


def _auth_calls(fake):
    return [c for c in fake.calls if "authRestApi" in c[1] or "getTicket" in c[1]]


# --------------------------------------------------------------------------- #
#  Tests (compatibles con pytest)
# --------------------------------------------------------------------------- #
def test_full_flow_three_views():
    """Las 3 vistas presentes -> registro creado y 3 imagenes subidas."""
    _, fake, record_id = _run(["frontal", "zenithal", "backward"])
    assert record_id == "REC123"
    assert set(fake.uploaded.keys()) == {
        config_zoho.ZOHO_FIELD_FRONTAL,
        config_zoho.ZOHO_FIELD_CENITAL,
        config_zoho.ZOHO_FIELD_TRACERA,
    }


def test_field_mapping_and_uploaded_bytes():
    """El campo correcto recibe la imagen correcta y con los BYTES reales."""
    _, fake, _ = _run(["frontal", "zenithal", "backward"])
    # frontal->Frontal, zenithal->Cenital, backward->Tracera
    assert fake.uploaded[config_zoho.ZOHO_FIELD_FRONTAL] == REAL_IMAGE_BYTES["frontal"]
    assert fake.uploaded[config_zoho.ZOHO_FIELD_CENITAL] == REAL_IMAGE_BYTES["zenithal"]
    assert fake.uploaded[config_zoho.ZOHO_FIELD_TRACERA] == REAL_IMAGE_BYTES["backward"]


def test_two_step_auth_sequence():
    """Se obtiene token Grima y luego token Zoho (Bearer -> Zoho-oauthtoken)."""
    _, fake, _ = _run(["frontal"])
    urls = [c[1] for c in fake.calls]
    assert any("authRestApi" in u for u in urls), "falto login Grima"
    assert any("getTicket" in u for u in urls), "falto getTicket"
    # El form add usa el token Zoho.
    form_call = next(c for c in fake.calls if c[1].endswith(f"/form/{config_zoho.ZOHO_FORM}"))
    assert form_call[2] == "Zoho-oauthtoken ZOHO_TOK"


def test_missing_view_skipped_record_still_created():
    """Falta 'zenithal': el registro se crea igual y solo se suben las otras 2."""
    _, fake, record_id = _run(["frontal", "backward"])
    assert record_id == "REC123"
    assert config_zoho.ZOHO_FIELD_CENITAL not in fake.uploaded
    assert set(fake.uploaded.keys()) == {
        config_zoho.ZOHO_FIELD_FRONTAL,
        config_zoho.ZOHO_FIELD_TRACERA,
    }


def test_no_views_still_creates_record():
    """Sin ninguna imagen clasificada: el registro se crea y no se sube nada."""
    _, fake, record_id = _run([])
    assert record_id == "REC123"
    assert fake.uploaded == {}


def test_retries_on_transient_error():
    """Dos 500 transitorios en el login Grima -> reintenta y termina OK."""
    assert config_zoho.NET_MAX_RETRIES >= 3, "el requisito pide >= 3 reintentos"
    _, fake, record_id = _run(["frontal"], transient_500=2)
    assert record_id == "REC123"
    grima_hits = [c for c in fake.calls if "authRestApi" in c[1]]
    # 2 respuestas 500 + 1 exitosa = 3 golpes al endpoint de login.
    assert len(grima_hits) == 3, f"esperaba 3 intentos de login, hubo {len(grima_hits)}"


def test_token_cache_reused_across_calls():
    """Segunda llamada dentro del TTL: no vuelve a autenticar (cache de tokens)."""
    _place_frames(["frontal"])
    fake = FakeZohoTransport()
    original = zoho_proxy.requests.request
    zoho_proxy.requests.request = fake
    try:
        proxy = ZohoEncendidoProxy()
        proxy.send_encendido()
        assert len(_auth_calls(fake)) == 2, "1a llamada: login + getTicket"
        fake.calls.clear()
        proxy.send_encendido()
        assert len(_auth_calls(fake)) == 0, "2a llamada no debe re-autenticar"
    finally:
        zoho_proxy.requests.request = original


# --------------------------------------------------------------------------- #
#  Runner manual
# --------------------------------------------------------------------------- #
def main():
    print("=" * 70)
    print("TESTS - Flujo de encendido Zoho Creator (Grima 2 pasos)")
    print(f"Frames reales: {IMAGES_DIR}")
    print("=" * 70)

    tests = [
        test_full_flow_three_views,
        test_field_mapping_and_uploaded_bytes,
        test_two_step_auth_sequence,
        test_missing_view_skipped_record_still_created,
        test_no_views_still_creates_record,
        test_retries_on_transient_error,
        test_token_cache_reused_across_calls,
    ]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"[OK]    {t.__name__} - {t.__doc__.strip()}")
        except AssertionError as e:
            failures += 1
            print(f"[FALLA] {t.__name__}: {e}")

    print("\n" + "=" * 70)
    if failures:
        print(f"RESULTADO: {failures} test(s) con fallas.")
        sys.exit(1)
    print("RESULTADO: todos los tests OK.")


if __name__ == "__main__":
    main()
