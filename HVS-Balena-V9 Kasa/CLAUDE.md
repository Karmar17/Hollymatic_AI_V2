# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Hollymatic Vision System (HVS) — a computer-vision safety interlock for a Hollymatic meat-patty machine (KP200), designed to run on a Raspberry Pi 4 under balenaOS. Cameras photograph the machine from three views; YOLO models classify each view and detect whether the 5 mandatory parts are correctly assembled. If everything is correct, the machine is powered on (via a TP-Link Kasa KP200 smart plug on the LAN); if not, a comparison PDF is generated and a Google Chat alert is sent. Every run is recorded in MySQL for monthly KPI reporting. There is also a two-step remote-authorization flow (Zoho Creator) and a remote calibration API.

Most code comments, docstrings, and log messages are in **Spanish** — match that when editing existing files.

## Architecture: four Docker services

The system is four independent containers (`docker-compose.yml`), sharing the internal Docker network and the `./secrets` + `.env` credentials. `db` has **no host port** — only reachable service-to-service by hostname `db`.

- **`app`** (`HVS-SAFIA`) — the vision system. Entry point `app/main.py`, launched via `app/start.sh` (which re-hydrates the Google service-account JSON from `GCP_SA_JSON`/`GCP_SA_B64`). Needs `/dev/video0` and the host `video` group. This is the core loop.
- **`db`** (`HVS-DB`) — MySQL, schema baked from `db/init/01_schema.sql`. See "Database" below.
- **`scheduler`** (`HVS-SCHEDULER`) — APScheduler (`scheduler/main.py`) for time-based jobs: nightly KP200 shutoff, cleaning reminder, and the **monthly KPI PDF report**. Reads the DB over the internal network. See `scheduler/README_REPORTE_MENSUAL.md` for forcing the monthly report by hand.
- **`api`** (`HVS-API`) — FastAPI + uvicorn (`api/run.py`), published on host port **81** (`81:8000`). JWT-protected `/calibrate` endpoint that toggles the Kasa plug remotely (45 s on/off). No DB, camera, or GPIO. See `api/PASOS_EJECUCION_API.txt`.

`app`, `scheduler`, and `api` each bind-mount their own source dir over `/app` (live code reload without rebuild) and share the same `src.*` import layout with `WORKDIR=/app`.

## The main vision loop (`app/main.py`)

Note: the loop is currently hardcoded to a dev path (`dev == 1`) with the physical GPIO button triggers commented out. The three real modes are:

1. **Turn-on run** (dev==1): clear `./temporal/images`, check cameras, and for each available camera run `HollyVisionSystem.full_processing()` → capture image → `inferencer.classify_view()` (frontal/zenithal/backward) → `inferencer.inference()` (YOLO detect/segment). Results accumulate in `config_models.RESULTS`. Then `correct_assambly()` validates detected classes against the required-assembly spec. If all mandatory parts pass → power on the machine + record a good attempt; otherwise → build a comparison PDF, upload to Drive, send the link via Google Chat, and record a bad attempt with the failed piece names.
2. **Shutdown**: power off the Kasa plug.
3. **Calibration/encendido request** (dev==3): capture + classify each camera, then `ZohoEncendidoProxy.send_encendido()` creates a "Pendiente" record in Zoho Creator and uploads the per-view images for two-step human authorization.

### Global mutable state — important

`config_models` (`app/src/configs/configmodels.py`) is a class used as a **global singleton via class attributes** (never instantiated — see its comment: intentionally not a constructor so all callers share one memory). `set_to_default()` resets it at the start of every run. Key fields: `RESULTS` (accumulated detections), `MANDATORY_ASSEMBLY` (piece-name → bool pass/fail), `MANDATORY_ASSEMBLY_NAMES` (per-view: detected-class → mandatory-piece-key mapping), `CAMERA_LOCATIONS`, `SEGMENTATION_MODELS`. When tracing detection→pass/fail logic, this is the shared blackboard everything reads and writes.

The **5 mandatory pieces** (`RAM_ASSEMBLY_AND_DRIVE_BAR`, `LOCK_SHAFT_ASSAMBLY`, `KOCUP_KOARM_AND_MOLDPLATE`, `ECCENTRIC_LEVER`, `TUMBLER`) are defined in three places that MUST stay in sync: `config_models.MANDATORY_ASSEMBLY` keys, the `mandatory_assemblies` seed rows in `db/init/01_schema.sql`, and the DB repository's name→id mapping.

### Models

YOLO weights (`.pt`) live under `app/models/{frontal,zenithal,backward,cameras}_models/`. Their paths come from `.env` (see `config` in `app/src/configs/configs.py`, e.g. `CLASSIFICATION_MODEL_PATH`, `LOCK_SHAFT_MODEL_PATH`, …). `model_loader.load_models()` loads one classification model + ≥3 segmentation model sets at startup and **raises `ValueError` if fewer than 3 load** — a missing/mispathed weight file is the usual cause of startup failure.

## Configuration

All runtime config is environment-driven. `app/src/configs/configs.py` (`class config`) reads every value from `.env` via `python-dotenv` and does eager type coercion at import time (e.g. `float(os.getenv(...))`, `.split(",")`) — a missing or empty `.env` var throws on import, not lazily. The other `config*.py` files (`configzoho`, `configmikasa`, `configmodels`, `configmessages`, `configRPI`, `configlogger`) wrap or extend these. In production (balena), values come from the balena dashboard's Device/Fleet variables, not `.env`.

## Database

Schema in `db/init/01_schema.sql`, applied **only when the `db_data` volume is empty** (MySQL init behavior) — to change the schema on an existing volume you must drop the volume. Three tables: `mandatory_assemblies` (catalog of the 5 pieces), `attempts` (one row per turn-on run, `is_bad` flag + timestamp), `bad_assemblies` (one row per failed piece per attempt, FK to both). `app` writes attempts via `app/src/db/repositories.py`; `scheduler` reads them for KPI reports.

## Commands

There is **no git repo, no linter, and no test runner config** (no pytest.ini/pyproject.toml). Type checking is configured via `pyrightconfig.json` (standard mode).

### Run / build (everything is Docker-first)
```bash
docker compose build                 # build all four images
docker compose up -d                 # start all services
docker compose up -d db scheduler    # start a subset
docker compose logs -f app           # follow one service's logs
docker compose exec app python /app/main.py   # run the main loop manually inside the container
```

### Tests
Tests are plain scripts / pytest files (network is mocked in the Zoho tests). They rely on `sys.path` insertion of the app root and real sample images in `tests/images/`. Run from inside the relevant service dir so `src.*` imports resolve:
```bash
# app tests (from app/)
cd app && pytest tests/test_zoho_encendido.py -s
python3 app/tests/test_zoho_encendido.py         # files also run standalone
# scheduler tests (from scheduler/)
cd scheduler && pytest tests/test_kpi_charts.py
```
`app/tests/real_zoho_encendido.py` hits the **real** Zoho/Grima APIs — don't run it casually.

### Force the monthly KPI report (normally day-1 cron)
```bash
docker compose exec scheduler \
  python -c "from src.executors.kpi_manager import kpi_manager; print(kpi_manager.generate_monthly_report())"
```
`generate_monthly_report(today=...)` always reports the month **before** `today`. Full details in `scheduler/README_REPORTE_MENSUAL.md`.

### Calibration API (dev)
Published on host port **81**. Docs at `http://localhost:81/docs`. `API_PASSWORD_HASH` must be **base64-encoded** in `.env` (docker compose interpolates the `$` in a raw bcrypt hash and corrupts it); on balena it can be a raw `$2b$...` hash. See `api/PASOS_EJECUCION_API.txt`.

## External integrations

- **Kasa KP200 smart plug** — `python-kasa` over the LAN (`MIKASA_IP:9999`), wrapped by `mikasa.py`. This is the physical power interlock. `discover_kp200()` runs at startup.
- **Google Chat** — webhook alerts (`gchat.py`), best-effort (failures never crash the loop).
- **Google Drive** — comparison PDFs / KPI reports uploaded via both the API (`gdrive.py`) and **rclone** (`rclone_GDrive.py`, `rclone.conf`); uses a service-account JSON in `./secrets`.
- **Zoho Creator** — two-step machine-authorization flow (`app/src/zoho/zoho_proxy.py`): login Grima → getTicket → create "Pendiente" record → upload per-view images.

## Error-handling convention

The production loop is built to **never crash** on a subsystem failure: nearly every external call is wrapped in try/except that logs `critical`/`warning` and returns/continues rather than raising. Network calls to Zoho use `_request_with_retries` (exponential backoff on timeouts/429/5xx). Preserve this fail-soft behavior — a failed Drive upload, Chat message, or DB write should degrade gracefully, not abort the run.

## Deployment

Production runs on a Raspberry Pi 4 via **balenaOS** (`balena.yml`, `prod/docker-compose.yml`, `prod/Dockerfile`) — a separate compose from the dev one at the root. Push with `balena push <fleet>`. Prod credentials are balena Device/Fleet variables, not `.env`. GPIO buttons (`gpiozero`, currently commented out in `main.py`) are the real triggers on-device instead of the `dev == N` branches.
