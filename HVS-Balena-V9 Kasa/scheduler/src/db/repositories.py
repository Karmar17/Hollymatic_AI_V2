from src.db.connection import db_connection
from src.db.models import Attempt


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
