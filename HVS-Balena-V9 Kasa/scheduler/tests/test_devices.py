"""
Smoke test MANUAL del scheduler contra hardware/red reales (enchufe KP200 en la
misma LAN, y dependencias instaladas). NO se ejecuta de forma automática.

Pensado para correrse dentro del contenedor / en el dispositivo. Uso:

    # Informa el estado del KP200 (no lo apaga):
    python3 tests/test_devices.py

    # Además, prueba el apagado REAL del KP200 (acción destructiva: apaga el enchufe):
    SMOKE_KP200_OFF=1 python3 tests/test_devices.py

    # Además, envía un mensaje de prueba a Google Chat (requiere SERVICE_ACCOUNT_PATH y
    # SPACE_ID; reutiliza la clase gchat):
    SMOKE_CHAT=1 python3 tests/test_devices.py

Requiere MIKASA_IP/USERNAME/PASSWORD en el entorno para el KP200.
"""
import os
import sys
import asyncio

SCHEDULER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCHEDULER_ROOT not in sys.path:
    sys.path.insert(0, SCHEDULER_ROOT)

import main as sched
from src.google.gchat import gchat


async def _smoke():
    print("[i] Conectando al KP200 (Kasa)...")
    await sched.controller.discover_device()
    print(f"[i] Estado KP200 is_on = {sched.controller.device.is_on}")

    if os.environ.get("SMOKE_KP200_OFF"):
        print("[i] Apagando KP200 (SMOKE_KP200_OFF=1)...")
        await sched.turn_off()

    if os.environ.get("SMOKE_CHAT"):
        print("[i] Enviando mensaje de prueba a Google Chat (SMOKE_CHAT=1)...")
        await asyncio.to_thread(gchat.send_advice, "🧪 Mensaje de prueba del contenedor scheduler.")

    print("[i] Smoke test finalizado.")


if __name__ == "__main__":
    asyncio.run(_smoke())
