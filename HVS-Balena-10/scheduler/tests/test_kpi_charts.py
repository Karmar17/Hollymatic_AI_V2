"""
Prueba de generación de las gráficas de KPI en PDF (contenedor `scheduler`).

Reproduce el render de los KPIs definidos en docs/KPIs.pdf usando DATOS DE MUESTRA
(no toca la base de datos ni Google). Sirve para validar visualmente el PDF antes de
cablear la persistencia SQLite y el job mensual real. La lógica de fechas y de armado
de gráficas está escrita para poder moverse tal cual al futuro
`scheduler/src/executors/kpi_manager.py`.

KPIs incluidos:
  - KPI 1 "Mal armados del último mes": conteo de intentos con falla en el mes anterior.
  - KPI 2 "% días de uso": días distintos con actividad / días del mes anterior.
  - Gráfica "normal": distribución de uso por hora del día durante el mes anterior.

Uso (genera el PDF con datos de muestra):
    python3 tests/test_kpi_charts.py
    # -> escribe scheduler/output/kpi_report_<YYYY-MM>.pdf e imprime la ruta

También es compatible con pytest:
    pytest tests/test_kpi_charts.py -s

Requiere `matplotlib` (solo para el PDF; las fechas y KPIs usan stdlib). Si falta,
la generación del PDF se SALTA con un mensaje claro (igual que el resto de los tests).
"""
import os
import sys
import re
import random
import datetime
import tempfile
import unittest

# Permite ejecutar el archivo directamente (python3 tests/...) y que el paquete `src`
# y `main` (que viven en scheduler/) sean importables, igual que los otros tests.
SCHEDULER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCHEDULER_ROOT not in sys.path:
    sys.path.insert(0, SCHEDULER_ROOT)

# Dependencias opcionales en el host de desarrollo. Si faltan, se SALTA.
# Las funciones de fechas, KPIs y render se importan del job real (kpi_manager)
# para probar exactamente el mismo código que genera el reporte mensual.
IMPORT_ERROR = None
try:
    from src.executors.kpi_manager import (
        prev_month_bounds, days_in_month, compute_kpis, build_kpi_pdf,
    )
except Exception as e:  # dependencias ausentes
    IMPORT_ERROR = e


def _require_charting():
    if IMPORT_ERROR is not None:
        raise unittest.SkipTest(f"Dependencias de graficado no disponibles: {IMPORT_ERROR}")


# --------------------------------------------------------------------------- #
#  Datos de muestra
# --------------------------------------------------------------------------- #
def build_mock_attempts(start, n_days, seed=42):
    """Genera intentos `(timestamp, is_bad)` repartidos en ~70% de los días del mes
    anterior, varios por día y en horario laboral. Determinístico vía `seed`."""
    rng = random.Random(seed)
    attempts = []
    active_days = sorted(rng.sample(range(1, n_days + 1), k=max(1, int(n_days * 0.7))))
    for day in active_days:
        for _ in range(rng.randint(1, 6)):
            ts = start.replace(day=day, hour=rng.randint(6, 18),
                               minute=rng.randint(0, 59), second=0, microsecond=0)
            attempts.append((ts, rng.random() < 0.18))  # ~18% mal armados
    attempts.sort(key=lambda pair: pair[0])
    return attempts


def build_mock_calibrations(start, n_days, seed=7):
    """Genera timestamps de calibración en ~25% de los días del mes anterior
    (1 o 2 por día). Determinístico vía `seed`."""
    rng = random.Random(seed)
    calibrations = []
    calib_days = sorted(rng.sample(range(1, n_days + 1), k=max(1, int(n_days * 0.25))))
    for day in calib_days:
        for _ in range(rng.randint(1, 2)):
            calibrations.append(start.replace(day=day, hour=rng.randint(6, 18),
                                              minute=rng.randint(0, 59), second=0, microsecond=0))
    calibrations.sort()
    return calibrations


# --------------------------------------------------------------------------- #
#  Tests (pytest-compatibles)
# --------------------------------------------------------------------------- #
def test_compute_kpis_known_values():
    """Con datos fijos, los KPIs salen exactos (KPI 1 y KPI 2)."""
    _require_charting()
    attempts = [
        (datetime.datetime(2025, 1, 5, 8), False),
        (datetime.datetime(2025, 1, 5, 9), True),
        (datetime.datetime(2025, 1, 6, 10), False),
        (datetime.datetime(2025, 1, 20, 14), True),
    ]
    kpis = compute_kpis(attempts, n_days=31)
    assert kpis["bad_count"] == 2                  # KPI 1: dos intentos con falla
    assert kpis["distinct_days"] == 3              # días 5, 6 y 20
    assert kpis["total"] == 4
    assert abs(kpis["usage_ratio"] - 3 / 31) < 1e-9  # KPI 2
    assert kpis["calib_count"] == 0                # sin calibraciones por defecto
    assert kpis["per_day_calib"] == {}


def test_compute_kpis_calibrations():
    """Las calibraciones se cuentan en total y por día del mes."""
    _require_charting()
    calibrations = [
        datetime.datetime(2025, 1, 5, 7),
        datetime.datetime(2025, 1, 5, 15),
        datetime.datetime(2025, 1, 12, 9),
    ]
    kpis = compute_kpis([], n_days=31, calibrations=calibrations)
    assert kpis["calib_count"] == 3
    assert kpis["per_day_calib"] == {5: 2, 12: 1}


def test_prev_month_bounds_for_known_date():
    """El mes anterior se calcula correctamente (incluye cruce de año)."""
    _require_charting()
    start, end = prev_month_bounds(datetime.date(2025, 1, 15))
    assert (start.year, start.month, start.day) == (2024, 12, 1)
    assert (end.year, end.month, end.day) == (2024, 12, 31)


def test_pdf_is_created():
    """El PDF se genera, no queda vacío y tiene 4 páginas
    (seguimiento diario, días de uso, uso por hora, intentos por día)."""
    _require_charting()
    start, _ = prev_month_bounds()
    n_days = days_in_month(start)
    kpis = compute_kpis(build_mock_attempts(start, n_days), n_days,
                        build_mock_calibrations(start, n_days))
    with tempfile.TemporaryDirectory() as tmp:
        out = build_kpi_pdf(kpis, start.strftime("%Y-%m"), os.path.join(tmp, "kpi.pdf"))
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0
        with open(out, "rb") as f:
            assert len(re.findall(rb"/Type\s*/Page\b", f.read())) == 4


# --------------------------------------------------------------------------- #
#  Runner manual: genera el PDF de muestra en scheduler/output/
# --------------------------------------------------------------------------- #
def main():
    print("=" * 70)
    print("PRUEBA - gráficas de KPI en PDF (datos de muestra)")
    print("=" * 70)

    # 1) Aserciones rápidas que no dependen de matplotlib.
    failures = 0
    for title, fn in [
        ("compute_kpis valores conocidos", test_compute_kpis_known_values),
        ("compute_kpis calibraciones", test_compute_kpis_calibrations),
        ("prev_month_bounds (cruce de año)", test_prev_month_bounds_for_known_date),
    ]:
        try:
            fn()
            print(f"[OK]    {title}")
        except unittest.SkipTest as e:
            print(f"[SKIP]  {title}: {e}")
        except AssertionError as e:
            failures += 1
            print(f"[FALLA] {title}: {e}")

    # 2) Generación real del PDF con datos de muestra.
    if IMPORT_ERROR is not None:
        print(f"[SKIP]  generar PDF: dependencias no disponibles ({IMPORT_ERROR})")
        print("        Instala con: pip install matplotlib python-dateutil")
    else:
        start, _ = prev_month_bounds()
        n_days = days_in_month(start)
        attempts = build_mock_attempts(start, n_days)
        calibrations = build_mock_calibrations(start, n_days)
        kpis = compute_kpis(attempts, n_days, calibrations)
        period = start.strftime("%Y-%m")
        out_path = os.path.join(SCHEDULER_ROOT, "output", f"kpi_report_{period}.pdf")
        build_kpi_pdf(kpis, period, out_path)
        print(f"[OK]    PDF generado para el periodo {period}:")
        print(f"        1. Activaciones totales = {kpis['total']} | "
              f"2. Calibraciones totales = {kpis['calib_count']} | "
              f"3. Malos armados = {kpis['bad_count']}")
        print(f"        -> {out_path}")

    print("=" * 70)
    if failures:
        print(f"RESULTADO: {failures} aserción(es) con fallas.")
        sys.exit(1)
    print("RESULTADO: OK.")


if __name__ == "__main__":
    main()
