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
import random
import calendar
import datetime
import tempfile
import unittest
from collections import Counter

# Permite ejecutar el archivo directamente (python3 tests/...) y que el paquete `src`
# y `main` (que viven en scheduler/) sean importables, igual que los otros tests.
SCHEDULER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCHEDULER_ROOT not in sys.path:
    sys.path.insert(0, SCHEDULER_ROOT)

# Dependencias opcionales en el host de desarrollo. Si faltan, se SALTA.
IMPORT_ERROR = None
try:
    import matplotlib
    matplotlib.use("Agg")  # backend headless (sin display en el contenedor/dispositivo)
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.backends.backend_pdf import PdfPages
except Exception as e:  # dependencias ausentes
    IMPORT_ERROR = e


def _require_charting():
    if IMPORT_ERROR is not None:
        raise unittest.SkipTest(f"Dependencias de graficado no disponibles: {IMPORT_ERROR}")


# --------------------------------------------------------------------------- #
#  Utilidades de fecha (mismas que usará el job mensual real)
# --------------------------------------------------------------------------- #
def prev_month_bounds(today=None):
    """Primer y último instante del mes anterior a `today` (hoy por defecto).

    Solo stdlib: restar un día al primer día del mes actual cae en el último día
    del mes anterior (maneja el cruce de año), y ese día es además el nº de días."""
    today = today or datetime.date.today()
    last_prev = today.replace(day=1) - datetime.timedelta(days=1)  # último día del mes anterior
    first_prev = last_prev.replace(day=1)
    start = datetime.datetime.combine(first_prev, datetime.time.min)
    end = datetime.datetime.combine(last_prev, datetime.time.max)
    return start, end


def days_in_month(any_date):
    """Número de días del mes de `any_date`."""
    return calendar.monthrange(any_date.year, any_date.month)[1]


# --------------------------------------------------------------------------- #
#  Datos de muestra + cálculo de KPIs
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


def compute_kpis(attempts, n_days):
    """Calcula los KPIs del PDF a partir de una lista de `(timestamp, is_bad)`."""
    distinct_days = {ts.date() for ts, _ in attempts}
    return {
        "per_hour": dict(Counter(ts.hour for ts, _ in attempts)),                 # gráfica "normal"
        "per_day": dict(Counter(ts.day for ts, _ in attempts)),
        "per_day_bad": dict(Counter(ts.day for ts, is_bad in attempts if is_bad)),
        "distinct_days": len(distinct_days),                                      # KPI 2 (numerador)
        "n_days": n_days,                                                         # KPI 2 (denominador)
        "usage_ratio": (len(distinct_days) / n_days) if n_days else 0.0,          # KPI 2
        "bad_count": sum(1 for _, is_bad in attempts if is_bad),                  # KPI 1
        "total": len(attempts),
    }


# --------------------------------------------------------------------------- #
#  Render del PDF (estilo de marca HOLLYMATIC AI SYSTEM)
# --------------------------------------------------------------------------- #
# Paleta tomada del PDF de referencia.
MAROON = "#6E1423"          # banda de encabezado
MAROON_DARK = "#3D0A12"     # acento izquierdo de la banda
BLUE_USE = "#4F7CEC"        # días de uso
LAVENDER_NOUSE = "#B79DE6"  # días de no uso
INK = "#1A1A1A"             # texto
PAGE_BG = "#F7F5F4"         # fondo de página
GREEN_OK = "#4C9F70"        # intentos correctos
RED_BAD = "#C0504D"         # intentos mal armados
PAGE_SIZE = (8.5, 8.5)      # página casi cuadrada (evita el aspecto alargado)


def _new_page():
    """Página con fondo y la banda de marca superior."""
    fig = plt.figure(figsize=PAGE_SIZE)
    fig.patch.set_facecolor(PAGE_BG)
    fig.add_artist(mpatches.Rectangle((0, 0.94), 1.0, 0.06, transform=fig.transFigure,
                                      facecolor=MAROON, edgecolor="none", zorder=5))
    fig.add_artist(mpatches.Rectangle((0, 0.94), 0.05, 0.06, transform=fig.transFigure,
                                      facecolor=MAROON_DARK, edgecolor="none", zorder=6))
    fig.text(0.075, 0.97, "HOLLYMATIC AI SYSTEM", color="white", fontsize=19,
             fontweight="bold", va="center", ha="left", zorder=7)
    return fig


def _title(fig, text, y):
    fig.text(0.5, y, text, color=INK, fontsize=21, fontweight="bold", ha="center")


def build_kpi_pdf(kpis, period_label, out_path):
    """Escribe el PDF de KPIs con el estilo de marca. Retorna `out_path`."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    uso = kpis["usage_ratio"]
    with PdfPages(out_path) as pdf:
        # ----- Página 1: resumen (pie de días de uso + datos de efectividad) -----
        fig = _new_page()
        _title(fig, "DÍAS DE USO:", 0.87)
        ax = fig.add_axes([0.18, 0.45, 0.64, 0.38])
        ax.set_aspect("equal")
        ax.pie(
            [uso, 1 - uso],
            labels=[f"Días de uso\n{uso * 100:.1f}%",
                    f"Días de no uso\n{(1 - uso) * 100:.1f}%"],
            colors=[BLUE_USE, LAVENDER_NOUSE],
            startangle=90, counterclock=False, labeldistance=1.12,
            textprops={"color": INK, "fontsize": 11},
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        _title(fig, "DATOS DE EFECTIVIDAD:", 0.34)
        rows = [
            ("Días de uso:", f"{uso * 100:.1f}%  ({kpis['distinct_days']} de {kpis['n_days']} días)"),
            ("Mal armados del último mes:", f"{kpis['bad_count']}"),
            ("Total de intentos:", f"{kpis['total']}"),
        ]
        y = 0.26
        for label, value in rows:
            fig.text(0.12, y, label, color=INK, fontsize=14, fontweight="bold", va="top")
            fig.text(0.58, y, value, color=INK, fontsize=14, fontweight="bold", va="top")
            y -= 0.065
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)

        # ----- Página 2: uso por hora del día (la "gráfica normal" del diagrama) -----
        fig = _new_page()
        _title(fig, f"USO POR HORA DEL DÍA — {period_label}", 0.87)
        ax = fig.add_axes([0.12, 0.16, 0.80, 0.62])
        hours = list(range(24))
        ax.bar(hours, [kpis["per_hour"].get(h, 0) for h in hours], color=BLUE_USE)
        ax.set_xlabel("Hora del día (0–23)")
        ax.set_ylabel("Intentos")
        ax.set_xticks(hours)
        ax.tick_params(labelsize=8)
        ax.grid(axis="y", alpha=0.3)
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)

        # ----- Página 3: intentos por día (correctos vs mal armados, apilados) -----
        fig = _new_page()
        _title(fig, f"INTENTOS POR DÍA — {period_label}", 0.87)
        ax = fig.add_axes([0.12, 0.16, 0.80, 0.62])
        days = list(range(1, kpis["n_days"] + 1))
        total = [kpis["per_day"].get(d, 0) for d in days]
        bad = [kpis["per_day_bad"].get(d, 0) for d in days]
        good = [t - b for t, b in zip(total, bad)]
        ax.bar(days, good, label="Correctos", color=GREEN_OK)
        ax.bar(days, bad, bottom=good, label="Mal armados", color=RED_BAD)
        ax.set_xlabel("Día del mes")
        ax.set_ylabel("Intentos")
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)
    return out_path


# --------------------------------------------------------------------------- #
#  Tests (pytest-compatibles)
# --------------------------------------------------------------------------- #
def test_compute_kpis_known_values():
    """Con datos fijos, los KPIs salen exactos (KPI 1 y KPI 2)."""
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


def test_prev_month_bounds_for_known_date():
    """El mes anterior se calcula correctamente (incluye cruce de año)."""
    start, end = prev_month_bounds(datetime.date(2025, 1, 15))
    assert (start.year, start.month, start.day) == (2024, 12, 1)
    assert (end.year, end.month, end.day) == (2024, 12, 31)


def test_pdf_is_created():
    """El PDF se genera y no queda vacío."""
    _require_charting()
    start, _ = prev_month_bounds()
    n_days = days_in_month(start)
    kpis = compute_kpis(build_mock_attempts(start, n_days), n_days)
    with tempfile.TemporaryDirectory() as tmp:
        out = build_kpi_pdf(kpis, start.strftime("%Y-%m"), os.path.join(tmp, "kpi.pdf"))
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0


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
        ("prev_month_bounds (cruce de año)", test_prev_month_bounds_for_known_date),
    ]:
        try:
            fn()
            print(f"[OK]    {title}")
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
        kpis = compute_kpis(attempts, n_days)
        period = start.strftime("%Y-%m")
        out_path = os.path.join(SCHEDULER_ROOT, "output", f"kpi_report_{period}.pdf")
        build_kpi_pdf(kpis, period, out_path)
        print(f"[OK]    PDF generado para el periodo {period}:")
        print(f"        % días de uso = {kpis['usage_ratio'] * 100:.1f}% "
              f"({kpis['distinct_days']}/{n_days}) | "
              f"mal armados = {kpis['bad_count']} | total intentos = {kpis['total']}")
        print(f"        -> {out_path}")

    print("=" * 70)
    if failures:
        print(f"RESULTADO: {failures} aserción(es) con fallas.")
        sys.exit(1)
    print("RESULTADO: OK.")


if __name__ == "__main__":
    main()
