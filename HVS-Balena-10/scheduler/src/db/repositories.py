from src.db.connection import db_connection
from src.db.models import Attempt, Calibration
from src.configs.configlogger import logger_config


class attempts_repository:
    """Lectura de intentos para el reporte mensual de KPIs (SQLAlchemy ORM)."""

    @staticmethod
    def attempts_in_range(start, end):
        """
        Retorna los intentos en [start, end] como una lista de tuplas
        `(timestamp: datetime, is_bad: bool)`, ordenada por timestamp.

        El formato mapea directo a `compute_kpis()` de kpi_manager.
        """
        session = db_connection.get_session()
        try:
            rows = (
                session.query(Attempt.timestamp, Attempt.is_bad)
                .filter(Attempt.timestamp.between(start, end))
                .order_by(Attempt.timestamp)
                .all()
            )
            return [(timestamp, bool(is_bad)) for timestamp, is_bad in rows]
        finally:
            session.close()


class calibrations_repository:
    """Lectura de calibraciones para el reporte mensual de KPIs (SQLAlchemy ORM)."""

    logger = logger_config.main_production_logger

    @staticmethod
    def calibrations_in_range(start, end):
        """
        Retorna los timestamps (`datetime`) de las calibraciones en [start, end],
        ordenados.

        Fail-soft: si la consulta falla (p.ej. la tabla `calibrations` aún no
        existe en un volumen viejo) retorna [] para que el reporte salga igual.
        """
        session = db_connection.get_session()
        try:
            rows = (
                session.query(Calibration.timestamp)
                .filter(Calibration.timestamp.between(start, end))
                .order_by(Calibration.timestamp)
                .all()
            )
            return [timestamp for (timestamp,) in rows]
        except Exception as e:
            calibrations_repository.logger.warning(
                f"No se pudieron leer las calibraciones de la DB; se reportan 0: {e}")
            return []
        finally:
            session.close()
