from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import json
import httpx
from datetime import datetime
from redis_manager import get_cronjob, r as redis_conn
import asyncio
import time

scheduler = BackgroundScheduler()

def run_script(script_path):
    asyncio.run(run_async_script(script_path))  # Ejecuta el job como coroutine

async def run_async_script(script_path):
    retries = 3
    for attempt in range(retries):
        try:
            data = validate_script_path(script_path)  # Validamos y obtenemos el script_path

            job_id = data.get("job_id", "unknown")
            if job_id != "unknown":
                job_data = get_cronjob(job_id)
                if job_data and job_data.get("paused"):
                    print(f"[CronManager] Job '{job_id}' está pausado. No se ejecutará.")
                    return

            url = data["url"]
            method = data.get("method", "GET").upper()

            print(f"[CronManager] Ejecutando: {method} {url}")

            async with httpx.AsyncClient() as client:
                if method == "POST":
                    print(f"[CronManager] Realizando POST a la URL: {url}")
                    res = await client.post(url)
                else:
                    print(f"[CronManager] Realizando GET a la URL: {url}")
                    res = await client.get(url)

            if not res.text.strip():
                raise ValueError("Respuesta vacía del servidor")

            if 'application/json' in res.headers.get('Content-Type', ''):
                try:
                    response_data = res.json()
                except ValueError:
                    raise ValueError(f"Respuesta no válida JSON: {res.text}")
            else:
                response_data = {
                    "url": url,
                    "method": method,
                    "status_code": res.status_code,
                    "response_text": res.text,
                    "content_type": res.headers.get('Content-Type', 'unknown'),
                    "timestamp": datetime.now().isoformat()
                }

            key = f"cronmanager_crons:{job_id}:{datetime.now().isoformat()}"
            redis_conn.set(key, json.dumps(response_data))
            print(f"[CronManager] Resultado guardado en Redis bajo la llave {key}")
            break  # Salimos del loop si la ejecución fue exitosa

        except Exception as e:
            if attempt < retries - 1:
                print(f"[CronManager] Intento fallido, reintentando ({attempt+1}/3)...")
                time.sleep(2)  # Espera entre intentos
            else:
                print(f"[CronManager] Error final: {e}")
                raise e  # Lanzamos el error si después de varios intentos falla

def validate_script_path(script_path):
    if isinstance(script_path, str):
        try:
            return json.loads(script_path)
        except json.JSONDecodeError:
            if script_path.startswith("http"):
                return {"url": script_path, "method": "GET"}
            else:
                raise ValueError("El script_path no es válido ni como JSON ni como URL.")
    return script_path  # Ya es un dict

def add_cronjob_to_scheduler(job_id, script_path, interval_seconds):
    scheduler.add_job(
        run_script,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=str(job_id),
        args=[script_path],
        replace_existing=True
    )

def load_jobs_from_redis():
    from redis_manager import get_all_cronjobs
    for job in get_all_cronjobs():
        add_cronjob_to_scheduler(job["id"], job["script_path"], job["interval_seconds"])

def start():
    scheduler.start()
