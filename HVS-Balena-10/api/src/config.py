"""Configuracion del servicio API leida del entorno.

Las variables MIKASA_* se reutilizan del proyecto (ya existen en .env / dashboard de balena).
Las variables JWT_* y API_* son nuevas y especificas de este servicio.
"""
import base64
import os

from dotenv import load_dotenv

# En dev el compose monta ./api:/app y carga .env via env_file; load_dotenv es un
# best-effort adicional por si se ejecuta fuera del contenedor.
load_dotenv()


def _resolve_bcrypt_hash(value: str) -> str:
    """Devuelve un hash bcrypt (`$2...`) a partir del valor del entorno.

    Docker Compose interpola los `$` de los valores del .env, lo que corromperia
    un hash bcrypt crudo (p.ej. `$2b$12$...` llegaria truncado). Para el .env se
    guarda el hash en base64 (sin `$`); aqui se decodifica. Si el valor ya es un
    hash bcrypt crudo (caso del dashboard de balena, que no interpola), se usa tal cual.
    """
    if not value:
        return ""
    if value.startswith("$2"):
        return value
    try:
        decoded = base64.b64decode(value, validate=True).decode("utf-8")
        if decoded.startswith("$2"):
            return decoded
    except Exception:
        pass
    return value


class Config:
    # --- Enchufe Kasa (KP200) ---
    MIKASA_IP = os.getenv("MIKASA_IP")
    MIKASA_USERNAME = os.getenv("MIKASA_USERNAME")
    MIKASA_PASSWORD = os.getenv("MIKASA_PASSWORD")

    # --- JWT ---
    # OJO: os.getenv(x, default) solo devuelve el default cuando la variable NO existe.
    # En balena, una variable declarada suelta en docker-compose pero sin valor se
    # inyecta como cadena vacia (""), que NO dispara el default. Usamos `or default`
    # para que tanto ausente como vacia caigan al valor por defecto.
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM") or "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES") or "30")
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS") or "7")

    # --- Credenciales de acceso a la API ---
    API_USERNAME = os.getenv("API_USERNAME", "")
    # Password EN CLARO (via .env). Si esta definido tiene PRIORIDAD sobre el hash.
    API_PASSWORD = os.getenv("API_PASSWORD", "")
    # Hash bcrypt del password (en base64 para el .env, o crudo `$2...` en balena).
    # Se usa como respaldo cuando API_PASSWORD esta vacio (p.ej. balena/prod).
    API_PASSWORD_HASH = _resolve_bcrypt_hash(os.getenv("API_PASSWORD_HASH", ""))

    # Duracion (segundos) de la fase encendida de la calibracion.
    CALIBRATION_SECONDS = int(os.getenv("CALIBRATION_SECONDS") or "45")


config = Config()
