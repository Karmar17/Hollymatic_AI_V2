"""API de calibracion remota de la Hollymatic (FastAPI).

Rutas:
  POST /auth/login    -> access + refresh token (usuario+password)
  POST /auth/refresh  -> nuevo access token (a partir de un refresh token)
  POST /calibrate     -> (protegida) dispara la calibracion en segundo plano (202)
"""
import json
import logging

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, model_validator

from src import auth, calibrate

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    level=logging.INFO,
)

app = FastAPI(title="Hollymatic Calibration API", version="1.0.0")


# --- Esquemas ---
class _JsonOrStringModel(BaseModel):
    """Base que acepta el body como objeto JSON o como string JSON.

    Algunos clientes (p.ej. Zoho Deluge) envian el cuerpo doble-codificado:
    en vez de un objeto `{...}` mandan un string `"{...}"`. Este validador
    detecta ese caso y lo parsea antes de validar los campos.
    """

    @model_validator(mode="before")
    @classmethod
    def _coerce_json_string(cls, data):
        if isinstance(data, (str, bytes, bytearray)):
            try:
                return json.loads(data)
            except (json.JSONDecodeError, ValueError):
                pass
        return data


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(_JsonOrStringModel):
    refresh_token: str


class LoginRequest(_JsonOrStringModel):
    username: str
    password: str


# --- Rutas de autenticacion ---
@app.post("/auth/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    if not auth.verify_credentials(body.username, body.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contrasena incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=auth.create_access_token(body.username),
        refresh_token=auth.create_refresh_token(body.username),
    )


@app.post("/auth/refresh", response_model=AccessTokenResponse)
async def refresh(body: RefreshRequest):
    username = auth.decode_refresh_token(body.refresh_token)
    return AccessTokenResponse(access_token=auth.create_access_token(username))


# --- Ruta protegida: calibracion ---
@app.post("/calibrate", status_code=status.HTTP_202_ACCEPTED)
async def trigger_calibrate(
    background_tasks: BackgroundTasks,
    user: str = Depends(auth.get_current_user),
):
    if calibrate.is_calibrating():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya hay una calibracion en curso",
        )
    background_tasks.add_task(calibrate.run_calibration)
    return {"status": "calibration_started"}


if __name__ == "__main__":
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=8000,
        workers=1,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
