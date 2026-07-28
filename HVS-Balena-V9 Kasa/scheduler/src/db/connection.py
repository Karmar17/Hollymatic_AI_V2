from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker

from src.configs.settings import config
from src.configs.configlogger import logger_config


class db_connection:
    """
    Motor y sesiones de SQLAlchemy para el contenedor `scheduler` (driver PyMySQL).

    El scheduler alcanza al contenedor `db` por la red interna de Docker
    (config.DB_HOST=db, resolución por nombre de servicio; sin exponer el puerto).
    Solo lee datos (reporte mensual de KPIs).
    """

    logger = logger_config.main_production_logger
    _engine = None
    _Session = None

    @staticmethod
    def _url():
        return URL.create(
            "mysql+pymysql",
            username=config.DB_USER,
            password=config.DB_PASSWORD,
            host=config.DB_HOST,
            port=config.DB_PORT,
            database=config.DB_NAME,
            query={"charset": "utf8mb4"},
        )

    @staticmethod
    def get_engine():
        if db_connection._engine is None:
            db_connection._engine = create_engine(
                db_connection._url(),
                pool_pre_ping=True,
                pool_recycle=3600,
                future=True,
            )
        return db_connection._engine

    @staticmethod
    def get_session():
        """Retorna una sesión nueva de SQLAlchemy (el llamador la cierra)."""
        if db_connection._Session is None:
            db_connection._Session = sessionmaker(bind=db_connection.get_engine(), future=True)
        return db_connection._Session()
