"""
Escritura de los intentos de armado en la base de datos (contenedor `app`).

Cada corrida del botón de encendido (un "intento") genera una fila en `attempts`
y, si el armado fue malo, una fila en `bad_assemblies` por cada pieza obligatoria
que salió mal (mapeando el nombre -> mandatory_assemblies.id).

Las operaciones son best-effort: un fallo de base de datos se registra en el log
pero NO interrumpe el loop de visión.
"""
from src.db.connection import db_connection
from src.db.models import Attempt, BadAssembly, MandatoryAssembly, Calibration
from src.configs.configlogger import logger_config


class attempts_repository:
    """Persistencia de intentos para los reportes de KPIs (los lee el `scheduler`)."""

    logger = logger_config.main_production_logger

    @staticmethod
    def record_attempt(is_bad, bad_piece_names, timestamp):
        """
        Inserta un Attempt (is_bad, timestamp, date) y, si is_bad, una fila
        BadAssembly por cada pieza mal armada en `bad_piece_names`, mapeando el
        nombre (clave de config_models.MANDATORY_ASSEMBLY) a mandatory_assemblies.id.

        Best-effort: loguea y continúa ante cualquier error.
        """
        session = db_connection.get_session()
        try:
            attempt = Attempt(
                is_bad=int(bool(is_bad)),
                timestamp=timestamp,
                date=timestamp.date(),
            )
            session.add(attempt)
            session.flush()  # obtener attempt.id antes de insertar las piezas

            if is_bad and bad_piece_names:
                ids = dict(
                    session.query(MandatoryAssembly.name, MandatoryAssembly.id)
                    .filter(MandatoryAssembly.name.in_(bad_piece_names))
                    .all()
                )
                for name in bad_piece_names:
                    mid = ids.get(name)
                    if mid is None:
                        attempts_repository.logger.warning(
                            f"Pieza '{name}' sin id en mandatory_assemblies; se omite.")
                        continue
                    session.add(BadAssembly(attempt_id=attempt.id, type=mid, bad_assembly=1))

            session.commit()
            attempts_repository.logger.info(
                f"Intento registrado en DB (is_bad={int(bool(is_bad))}, "
                f"piezas_malas={len(bad_piece_names) if bad_piece_names else 0}).")
        except Exception as e:
            session.rollback()
            attempts_repository.logger.critical(f"No se pudo registrar el intento en DB: {e}")
        finally:
            session.close()


class calibrations_repository:
    """Persistencia de las solicitudes de calibración (las lee el `scheduler` para el reporte mensual)."""

    logger = logger_config.main_production_logger
    _table_checked = False

    @staticmethod
    def _ensure_table():
        """
        Crea la tabla `calibrations` si no existe (idempotente).

        El esquema de db/init solo se aplica con el volumen vacío; esto permite
        usar la tabla en volúmenes db_data ya existentes sin borrarlos.
        """
        if not calibrations_repository._table_checked:
            Calibration.__table__.create(bind=db_connection.get_engine(), checkfirst=True)
            calibrations_repository._table_checked = True

    @staticmethod
    def record_calibration(timestamp):
        """
        Inserta una fila en `calibrations` (timestamp, date).

        Best-effort: loguea y continúa ante cualquier error.
        """
        session = None
        try:
            calibrations_repository._ensure_table()
            session = db_connection.get_session()
            session.add(Calibration(timestamp=timestamp, date=timestamp.date()))
            session.commit()
            calibrations_repository.logger.info("Calibración registrada en DB.")
        except Exception as e:
            if session is not None:
                session.rollback()
            calibrations_repository.logger.critical(f"No se pudo registrar la calibración en DB: {e}")
        finally:
            if session is not None:
                session.close()
