from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import json
import httpx
from datetime import datetime
from redis_manager import get_cronjob, r
import asyncio

scheduler = BackgroundScheduler()

def run_script(script_path):
    asyncio.run(run_async_script(script_path))  # Ejecuta el job como coroutine
def run_script(script_path):
    asyncio.run(run_async_script(script_path))  # Ejecuta el job como coroutine
async def run_async_script(script_path):
    try:
        data = json.loads(script_path)  # Suponiendo que el script_path es un JSON
        url = data["url"]
        method = data.get("method", "GET").upper()

        # Imprime la URL y el método antes de ejecutar la solicitud
        print(f"[CronManager] Ejecutando: {method} {url}")

        async with httpx.AsyncClient() as client:
            if method == "POST":
                print(f"[CronManager] Realizando POST a la URL: {url}")
                res = await client.post(url)
            else:
                print(f"[CronManager] Realizando GET a la URL: {url}")
                res = await client.get(url)

        # Verifica si la respuesta está vacía
        if not res.text.strip():
            raise ValueError("Respuesta vacía del servidor")

        # Verifica si la respuesta es JSON
        if 'application/json' in res.headers.get('Content-Type', ''):
            try:
                response_data = res.json()  # Intenta parsear la respuesta como JSON
            except ValueError:
                raise ValueError(f"Respuesta no válida JSON: {res.text}")
        else:
            # Si la respuesta no es JSON, pero es HTML, la manejamos como texto
            response_data = {
                "url": url,
                "method": method,
                "status_code": res.status_code,
                "response_text": res.text,  # Almacena el contenido HTML completo
                "content_type": res.headers.get('Content-Type', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }

        job_id = data.get("job_id", "unknown")
        key = f"cronmanager_crons:{job_id}:{datetime.now().isoformat()}"
        redis_conn.set(key, json.dumps(response_data))
        print(f"[CronManager] Resultado guardado en Redis bajo la llave {key}")

    except Exception as e:
        print(f"[CronManager] Error al ejecutar el job: {e}")

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
