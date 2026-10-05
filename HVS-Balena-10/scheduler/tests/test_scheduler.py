"""
Tests del contenedor `scheduler` (apagado del KP200 + aviso a Google Chat).

Cubre la lógica del agendador sin depender de hardware/red, usando mocks:
  1. turn_off(): apaga el KP200 reutilizando SmartDeviceController.update_plugs(False).
  2. night_off(): si el enchufe seguía encendido, avisa a Google Chat (clase gchat) y
     apaga el KP200; si ya estaba apagado, no hace nada.

(La hidratación de la cuenta de servicio la realiza start.sh antes de lanzar main.py.)

Uso (validación manual):
    python3 tests/test_scheduler.py

También es compatible con pytest:
    pytest tests/test_scheduler.py -s

Requiere las dependencias del scheduler (apscheduler, python-kasa, google-auth,
google-api-python-client, dotenv). Si faltan, los tests se SALTAN con un mensaje
claro (igual que en el contenedor app).
"""
import os
import sys
import asyncio
import unittest
from unittest import mock

# Permite ejecutar el archivo directamente (python3 tests/...) y que el paquete `src`
# y `main` (que viven en scheduler/) sean importables.
SCHEDULER_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCHEDULER_ROOT not in sys.path:
    sys.path.insert(0, SCHEDULER_ROOT)

# Import del código bajo prueba. Si faltan dependencias, se SALTA.
sched = None
IMPORT_ERROR = None
try:
    import main as sched  # necesita apscheduler, python-kasa, google-*, dotenv
except Exception as e:  # dependencias ausentes en el host de desarrollo
    IMPORT_ERROR = e


def _require_scheduler():
    if sched is None:
        raise unittest.SkipTest(f"Dependencias del scheduler no disponibles: {IMPORT_ERROR}")


def _run(coro):
    """Ejecuta una corutina y espera además a las tareas en segundo plano que haya
    creado (p.ej. la notificación de night_off, lanzada con create_task), para que los
    asserts sean deterministas."""
    async def _wrapper():
        await coro
        pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)
    asyncio.run(_wrapper())


# --------------------------------------------------------------------------- #
#  turn_off / night_off (KP200 vía SmartDeviceController + aviso gchat)
# --------------------------------------------------------------------------- #
def test_turn_off_calls_update_plugs_false():
    """turn_off apaga el KP200 con update_plugs(False)."""
    _require_scheduler()
    fake = mock.MagicMock()
    fake.update_plugs = mock.AsyncMock()
    with mock.patch.object(sched, "controller", fake):
        _run(sched.turn_off())
    fake.update_plugs.assert_awaited_once_with(False)


def test_night_off_when_on_notifies_and_turns_off():
    """Si el enchufe seguía encendido: avisa a Google Chat (gchat) y apaga el KP200."""
    _require_scheduler()
    fake = mock.MagicMock()
    fake.discover_device = mock.AsyncMock()
    fake.update_plugs = mock.AsyncMock()
    fake.device = mock.MagicMock()
    fake.device.is_on = True
    fake_gchat = mock.MagicMock()
    fake_gchat.send_advice = mock.MagicMock(return_value=0)
    with mock.patch.object(sched, "controller", fake), mock.patch.object(sched, "gchat", fake_gchat):
        _run(sched.night_off())
    fake.discover_device.assert_awaited_once()
    fake_gchat.send_advice.assert_called_once()          # notificación enviada (en hilo)
    fake.update_plugs.assert_awaited_once_with(False)    # turn_off ejecutado


def test_night_off_when_off_does_nothing():
    """Si el enchufe ya estaba apagado: ni avisa ni vuelve a apagar."""
    _require_scheduler()
    fake = mock.MagicMock()
    fake.discover_device = mock.AsyncMock()
    fake.update_plugs = mock.AsyncMock()
    fake.device = mock.MagicMock()
    fake.device.is_on = False
    fake_gchat = mock.MagicMock()
    fake_gchat.send_advice = mock.MagicMock()
    with mock.patch.object(sched, "controller", fake), mock.patch.object(sched, "gchat", fake_gchat):
        _run(sched.night_off())
    fake.discover_device.assert_awaited_once()
    fake.update_plugs.assert_not_awaited()
    fake_gchat.send_advice.assert_not_called()


# --------------------------------------------------------------------------- #
#  Runner manual
# --------------------------------------------------------------------------- #
def main():
    print("=" * 70)
    print("TESTS - scheduler (KP200 + aviso Google Chat)")
    print("=" * 70)

    tests = [
        ("turn_off -> update_plugs(False)", test_turn_off_calls_update_plugs_false),
        ("night_off encendido -> avisa y apaga", test_night_off_when_on_notifies_and_turns_off),
        ("night_off apagado -> sin acción", test_night_off_when_off_does_nothing),
    ]
    failures = skipped = 0
    for title, fn in tests:
        try:
            fn()
            print(f"[OK]    {title}")
        except unittest.SkipTest as e:
            skipped += 1
            print(f"[SKIP]  {title}: {e}")
        except AssertionError as e:
            failures += 1
            print(f"[FALLA] {title}: {e}")
        except Exception as e:
            failures += 1
            print(f"[ERROR] {title}: {e}")

    print("=" * 70)
    if failures:
        print(f"RESULTADO: {failures} test(s) con fallas.")
        sys.exit(1)
    if skipped:
        print(f"RESULTADO: {skipped} test(s) SALTADOS por dependencias; el resto OK.")
    else:
        print("RESULTADO: todos OK.")


if __name__ == "__main__":
    main()
