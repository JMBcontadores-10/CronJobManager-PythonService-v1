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
    # Ejecuta el job como coroutine y devuelve el resultado
    result = asyncio.run(run_async_script(script_path))
    return result

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
                    return None
            
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
            
            if job_id != "unknown":
                key = f"cronmanager_crons:{job_id}:{datetime.now().isoformat()}"
                redis_conn.set(key, json.dumps(response_data))
                print(f"[CronManager] Resultado guardado en Redis bajo la llave {key}")
            
            return response_data  # Devolvemos los datos de la respuesta
        
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
    # Asegurarnos de que script_path sea un diccionario
    if isinstance(script_path, str):
        script_path = validate_script_path(script_path)
    
    # Añadir el job_id al script_path para que run_script sepa a qué job pertenece
    script_path_with_id = dict(script_path)  # Crear una copia para no modificar el original
    script_path_with_id["job_id"] = job_id
    
    print(f"[CronManager] Añadiendo job {job_id} al scheduler con interval={interval_seconds}s")
    
    # Asegúrate de que el scheduler está inicializado y funcionando
    if not scheduler.running:
        print("[CronManager] Iniciando scheduler porque no estaba ejecutándose")
        scheduler.start()
    
    # Eliminar el job anterior si existe
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
        print(f"[CronManager] Job anterior con ID {job_id} eliminado para reemplazarlo")
    
    # Añadir el job con el intervalo especificado
    scheduler.add_job(
        run_script,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id=str(job_id),
        args=[script_path_with_id],
        replace_existing=True
    )
    
    # Verificar que el job se ha añadido correctamente
    job = scheduler.get_job(job_id)
    if job:
        print(f"[CronManager] Job {job_id} añadido correctamente al scheduler")
        print(f"[CronManager] Próxima ejecución: {job.next_run_time}")
    else:
        print(f"[CronManager] Error: No se pudo añadir el job {job_id} al scheduler")
        
def load_jobs_from_redis():
    from redis_manager import get_all_cronjobs
    jobs = get_all_cronjobs()
    print(f"[CronManager] Cargando {len(jobs)} trabajos desde Redis...")
    
    for job in jobs:
        if job.get("paused", False):
            print(f"[CronManager] Job '{job['id']}' está pausado, no se añadirá al scheduler")
            continue
        
        print(f"[CronManager] Añadiendo job '{job['name']}' (ID: {job['id']}) al scheduler")
        add_cronjob_to_scheduler(job["id"], job["script_path"], job["interval_seconds"])

def start():
    if not scheduler.running:
        scheduler.start()
        print("[CronManager] Scheduler iniciado correctamente")
    else:
        print("[CronManager] El scheduler ya está en ejecución")