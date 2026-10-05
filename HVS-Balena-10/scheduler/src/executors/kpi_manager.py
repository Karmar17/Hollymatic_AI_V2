"""
Generación del reporte mensual de KPIs en PDF (contenedor `scheduler`).

La lógica de fechas y de armado de gráficas se trasladó tal cual desde
`scheduler/tests/test_kpi_charts.py` (que la validó con datos de muestra). Aquí
se alimenta de DATOS REALES leídos de la base de datos vía
`scheduler.src.db.repositories.attempts_repository`.

KPIs incluidos (definidos en docs/KPIs.pdf):
  - Página 1 "Seguimiento diario": gráfica de líneas de activaciones y
    calibraciones por día + resumen (activaciones totales, calibraciones
    totales, malos armados).
  - KPI 1 "Mal armados del último mes": conteo de intentos con falla.
  - KPI 2 "% días de uso": días distintos con actividad / días del mes anterior.
  - Gráfica "uso por hora del día" y gráfica "intentos por día" (correctos vs falla).
"""
import os
import calendar
import datetime
from collections import Counter

import matplotlib
matplotlib.use("Agg")  # backend headless (sin display en el contenedor/dispositivo)
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.ticker import MaxNLocator

from src.db.repositories import attempts_repository, calibrations_repository
from src.google.gdrive import gdrive
from src.google.gchat import gchat
from src.configs.configlogger import logger_config

# Raíz del contenedor scheduler (.../scheduler) -> los PDFs van a .../scheduler/output
SCHEDULER_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --------------------------------------------------------------------------- #
#  Utilidades de fecha
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


def compute_kpis(attempts, n_days, calibrations=()):
    """Calcula los KPIs del PDF a partir de una lista de `(timestamp, is_bad)`
    y de la lista de timestamps de calibraciones."""
    distinct_days = {ts.date() for ts, _ in attempts}
    return {
        "per_hour": dict(Counter(ts.hour for ts, _ in attempts)),                 # gráfica "normal"
        "per_day": dict(Counter(ts.day for ts, _ in attempts)),
        "per_day_bad": dict(Counter(ts.day for ts, is_bad in attempts if is_bad)),
        "distinct_days": len(distinct_days),                                      # KPI 2 (numerador)
        "n_days": n_days,                                                         # KPI 2 (denominador)
        "usage_ratio": (len(distinct_days) / n_days) if n_days else 0.0,          # KPI 2
        "bad_count": sum(1 for _, is_bad in attempts if is_bad),                  # KPI 1
        "total": len(attempts),                                                   # activaciones totales
        "per_day_calib": dict(Counter(ts.day for ts in calibrations)),
        "calib_count": len(calibrations),                                         # calibraciones totales
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
ORANGE_CALIB = "#E08E2B"    # calibraciones
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


def _data_rows(fig, rows, y):
    """Escribe filas `(etiqueta, valor)` en negritas empezando en `y`."""
    for label, value in rows:
        fig.text(0.12, y, label, color=INK, fontsize=14, fontweight="bold", va="top")
        fig.text(0.62, y, value, color=INK, fontsize=14, fontweight="bold", va="top")
        y -= 0.065


def build_kpi_pdf(kpis, period_label, out_path):
    """Escribe el PDF de KPIs con el estilo de marca. Retorna `out_path`."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    uso = kpis["usage_ratio"]
    with PdfPages(out_path) as pdf:
        # ----- Página 1: seguimiento diario (activaciones vs calibraciones) -----
        fig = _new_page()
        _title(fig, f"SEGUIMIENTO DIARIO — {period_label}", 0.87)
        ax = fig.add_axes([0.12, 0.42, 0.80, 0.40])
        days = list(range(1, kpis["n_days"] + 1))
        ax.plot(days, [kpis["per_day"].get(d, 0) for d in days],
                marker="o", markersize=4, linewidth=2, color=BLUE_USE, label="Activaciones")
        ax.plot(days, [kpis["per_day_calib"].get(d, 0) for d in days],
                marker="o", markersize=4, linewidth=2, color=ORANGE_CALIB, label="Calibraciones")
        ax.set_xlabel("Día del mes")
        ax.set_ylabel("Cantidad")
        ax.set_xticks(days)
        ax.set_xlim(0.5, kpis["n_days"] + 0.5)
        ax.set_ylim(bottom=0)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        ax.tick_params(labelsize=8)
        ax.legend()
        ax.grid(axis="y", alpha=0.3)
        _title(fig, "DATOS DEL MES:", 0.31)
        _data_rows(fig, [
            ("1. Activaciones totales:", f"{kpis['total']}"),
            ("2. Calibraciones totales:", f"{kpis['calib_count']}"),
            ("3. Malos armados:", f"{kpis['bad_count']}"),
        ], 0.24)
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)

        # ----- Página 2: días de uso (pie) -----
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
        _data_rows(fig, [
            ("Días de uso:", f"{uso * 100:.1f}%  ({kpis['distinct_days']} de {kpis['n_days']} días)"),
        ], 0.26)
        pdf.savefig(fig, facecolor=fig.get_facecolor())
        plt.close(fig)

        # ----- Página 3: uso por hora del día (la "gráfica normal" del diagrama) -----
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

        # ----- Página 4: intentos por día (correctos vs mal armados, apilados) -----
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


class kpi_manager:
    """Orquesta el reporte mensual: lee la DB, arma el PDF, lo sube a Drive y avisa por Chat."""

    logger = logger_config.main_production_logger

    @staticmethod
    def generate_monthly_report(today=None):
        """
        Genera el PDF de KPIs del mes anterior a `today` (hoy por defecto),
        lo sube a Drive y manda el link por Google Chat. Retorna la ruta del PDF.
        """
        start, end = prev_month_bounds(today)
        period = start.strftime("%Y-%m")
        n_days = days_in_month(start)

        attempts = attempts_repository.attempts_in_range(start, end)
        kpi_manager.logger.info(
            f"Reporte de KPIs {period}: {len(attempts)} intentos leídos de la base de datos.")

        calibrations = calibrations_repository.calibrations_in_range(start, end)
        kpi_manager.logger.info(
            f"Reporte de KPIs {period}: {len(calibrations)} calibraciones leídas de la base de datos.")

        kpis = compute_kpis(attempts, n_days, calibrations)
        out_path = os.path.join(SCHEDULER_ROOT, "output", f"kpi_report_{period}.pdf")
        build_kpi_pdf(kpis, period, out_path)

        summary = (
            f"1. Activaciones totales: {kpis['total']}\n"
            f"2. Calibraciones totales: {kpis['calib_count']}\n"
            f"3. Malos armados: {kpis['bad_count']}\n")
        link = gdrive.upload_and_get_link(out_path)
        if link:
            gchat.send_advice(
                f"📊 Reporte de KPIs de {period} (Hollymatic):\n"
                f"{summary}"
                f"📄 PDF: {link}")
        else:
            gchat.send_advice(
                f"📊 Reporte de KPIs de {period} generado, pero no se pudo subir el PDF a Drive.\n"
                f"{summary}")

        return out_path
