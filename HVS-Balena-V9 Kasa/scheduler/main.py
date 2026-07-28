import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.google.gchat import gchat
from src.configs.configlogger import logger_config
from src.executors.kp200_manager import kp200
from src.executors.kpi_manager import kpi_manager

logger = logger_config.main_production_logger


async def night_off():
    # Mismo flujo que shut_down_button.is_held del app (app/main.py:115-119):
    # avisar por Chat -> desenergizar -> loggear.
    gchat.send_advice("Buenas noches, se ejecutó la desenergización programada "
                      "de Hollymatic el día de hoy.")
    await kp200.night_off()
    logger.info("Apagado")

async def clean():
    logger.info("Inicio de recordatorio de limpieza")
    try:
        gchat.send_advice("Recordatorio para limpiar el equipo Hollymatic Link: https://drive.google.com/file/d/1_Mx_OkZRkYZ1GPKQCtVEhC_RvbeVYQfe/view?usp=sharing")
        logger.info("Recordatorio enviado")
    except:
        logger.critical("No se ha podido enviar el recordatorio de limpieza")


async def kpi_report():
    """Reporte mensual de KPIs (día 1): lee la base de datos, arma el PDF,
    lo sube a Drive y manda el link por Google Chat."""
    logger.info("Generando reporte mensual de KPIs...")
    try:
        out = kpi_manager.generate_monthly_report()
        logger.info(f"Reporte de KPIs generado: {out}")
    except Exception as e:
        logger.critical(f"No se pudo generar el reporte mensual de KPIs debido a: {e}")



async def main():

    scheduler = AsyncIOScheduler(timezone="America/Los_Angeles")
    scheduler.add_job(night_off, trigger='cron',hour='22', minute='30')
    scheduler.add_job(clean, trigger='cron',hour='16',minute='30')
    # Reporte mensual de KPIs: el día 1 de cada mes a las 06:00 (hora local).
    scheduler.add_job(kpi_report, trigger='cron', day='1', hour='8', minute='1')

    scheduler.start()
    logger.log_startup("[START] AsyncIOScheduler iniciado.")

    try:
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
