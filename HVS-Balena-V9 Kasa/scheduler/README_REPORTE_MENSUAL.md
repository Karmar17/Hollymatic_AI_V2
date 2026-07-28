# Forzar el reporte mensual de KPIs vía Docker

El reporte mensual de KPIs lo genera el contenedor **`scheduler`** (`HVS-SCHEDULER`).
Normalmente se dispara solo el **día 1 de cada mes a las 06:00** (hora `America/Los_Angeles`)
mediante APScheduler (ver `scheduler/main.py`):

```python
scheduler.add_job(kpi_report, trigger='cron', day='1', hour='6', minute='0')
```

Esa tarea llama a `kpi_manager.generate_monthly_report()`, que:

1. Lee los intentos del **mes anterior** desde la base de datos (`db`).
2. Arma el PDF de KPIs en `scheduler/output/kpi_report_<AAAA-MM>.pdf`.
3. Sube el PDF a Google Drive.
4. Envía el link por Google Chat.

Este documento explica cómo **forzar esa ejecución a mano**, sin esperar al día 1.

---

## Requisitos previos

- Los servicios deben estar levantados (al menos `db` y `scheduler`):

  ```bash
  docker compose up -d db scheduler
  ```

- El contenedor `scheduler` necesita poder leer la DB y tener la cuenta de
  servicio de Google montada (`./secrets` → `/app/secrets`) y las variables del
  `.env` (`DB_*`, `DRIVE_FOLDER_ID`, `SERVICE_ACCOUNT_PATH`, `GCP_SA_B64`/`GCP_SA_JSON`).

> Nota: el `WORKDIR` del contenedor es `/app` y el código está bajo `/app/src`,
> por eso los comandos importan `from src.executors.kpi_manager import kpi_manager`.

---

## Opción A — Forzar el reporte del **mes anterior** (caso normal)

Es exactamente lo que hace la tarea agendada. Ejecuta un comando puntual dentro
del contenedor ya corriendo:

```bash
docker compose exec scheduler \
  python -c "from src.executors.kpi_manager import kpi_manager; print(kpi_manager.generate_monthly_report())"
```

- Genera el PDF del mes anterior a **hoy**.
- Lo sube a Drive y manda el link por Chat (igual que la ejecución automática).
- Imprime en consola la ruta del PDF dentro del contenedor
  (`/app/output/kpi_report_<AAAA-MM>.pdf`).

Si los contenedores **no** están levantados, usa `run --rm` en lugar de `exec`:

```bash
docker compose run --rm scheduler \
  python -c "from src.executors.kpi_manager import kpi_manager; print(kpi_manager.generate_monthly_report())"
```

---

## Opción B — Forzar el reporte de **un mes concreto**

`generate_monthly_report(today=...)` reporta siempre el **mes anterior** a la
fecha `today` que le pases. Para forzar el reporte de un mes `M`, pasa cualquier
día del mes **siguiente** (`M+1`).

Ejemplo — forzar el reporte de **mayo 2026** (pasando un día de junio 2026):

```bash
docker compose exec scheduler python -c "\
import datetime; \
from src.executors.kpi_manager import kpi_manager; \
print(kpi_manager.generate_monthly_report(today=datetime.date(2026, 6, 1)))"
```

Ejemplo — forzar el reporte de **junio 2026** (pasando un día de julio 2026):

```bash
docker compose exec scheduler python -c "\
import datetime; \
from src.executors.kpi_manager import kpi_manager; \
print(kpi_manager.generate_monthly_report(today=datetime.date(2026, 7, 1)))"
```

| Reporte que quieres | Valor de `today` a pasar |
| ------------------- | ------------------------ |
| Mayo 2026           | `datetime.date(2026, 6, 1)` |
| Junio 2026          | `datetime.date(2026, 7, 1)` |
| Diciembre 2025      | `datetime.date(2026, 1, 1)` |

---

## Recuperar el PDF generado

El PDF queda dentro del contenedor en `/app/output/`. Como el compose monta
`./scheduler:/app` (bind mount), también aparece en el host en:

```
scheduler/output/kpi_report_<AAAA-MM>.pdf
```

Si en tu entorno **no** hubiera bind mount, cópialo a mano:

```bash
docker compose cp scheduler:/app/output/kpi_report_2026-05.pdf ./
```

---

## Verificar que funcionó

- **Logs del contenedor** (busca `Generando reporte mensual de KPIs...` y
  `Reporte de KPIs generado: ...`):

  ```bash
  docker compose logs -f scheduler
  ```

- **Google Chat**: debe llegar un mensaje con el resumen y el link al PDF.
- **Google Drive**: el PDF aparece en la carpeta `DRIVE_FOLDER_ID`.

---

## Solución de problemas

| Síntoma | Causa probable | Acción |
| ------- | -------------- | ------ |
| `Can't connect to MySQL` / timeout de DB | El contenedor `db` no está listo | `docker compose up -d db` y reintenta |
| `No se pudo generar el reporte... ` en logs | Falta la cuenta de servicio o las credenciales | Verifica `./secrets/` y `GCP_SA_B64`/`GCP_SA_JSON` en `.env` |
| Mensaje "no se pudo subir el PDF a Drive" | Permisos/`DRIVE_FOLDER_ID` de Drive | Revisa que la service account tenga acceso a la carpeta |
| PDF con 0 intentos / vacío | No hay datos del mes en la DB | Confirma el mes objetivo (Opción B) y que existan registros |

---

## Resumen rápido

```bash
# Mes anterior (lo normal)
docker compose exec scheduler \
  python -c "from src.executors.kpi_manager import kpi_manager; print(kpi_manager.generate_monthly_report())"

# Un mes concreto (p. ej. mayo 2026 -> pasar un día de junio)
docker compose exec scheduler python -c "\
import datetime; from src.executors.kpi_manager import kpi_manager; \
print(kpi_manager.generate_monthly_report(today=datetime.date(2026, 6, 1)))"
```
