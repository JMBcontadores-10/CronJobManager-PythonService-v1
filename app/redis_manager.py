import redis
import json

from datetime import datetime

r = redis.Redis(host="172.18.203.157", port=6379, db=2, decode_responses=True)


def connect_to_redis():
    global r
    try:
        r.ping()
        print("[Redis] Conexión exitosa.")
    except redis.exceptions.ConnectionError as e:
        print(f"[Redis] Error de conexión: {e}")
        raise e

def save_cronjob(job_id: str, data: dict):
    data["paused"] = data.get("paused", False)  # Default: no está pausado
    r.set(f"cronjob:{job_id}", json.dumps(data))
    print(f"[Redis] Job {job_id} guardado correctamente")

def get_cronjob(job_id: str):
    data = r.get(f"cronjob:{job_id}")
    job = json.loads(data) if data else None
    if job is None:
        print(f"[CronManager] Job con ID {job_id} no encontrado.")
    else:
        if 'paused' not in job:
            job['paused'] = False  # Asignar el valor por defecto si no existe
        print(f"[CronManager] Job cargado: {job}")
    return job

def get_all_cronjobs():
    keys = r.keys("cronjob:*")
    jobs = []
    for k in keys:
        data = r.get(k)
        job = json.loads(data)
        if 'paused' not in job:
            job['paused'] = False  # Valor por defecto si no existe
        jobs.append(job)
    print(f"[Redis] Se encontraron {len(jobs)} trabajos en Redis")
    return jobs

def delete_cronjob(job_id: str):
    r.delete(f"cronjob:{job_id}")
    print(f"[Redis] Job {job_id} eliminado de Redis")

def save_cronjob_response(job_id, response):
    try:
        # Convertir la respuesta a JSON
        response_json = json.dumps(response)
        # Guardar la respuesta en Redis con un timestamp único
        timestamp = datetime.now().isoformat()  # O cualquier otra forma de obtener un timestamp
        key = f"cronjob_response:{job_id}:{timestamp}"
        r.set(key, response_json)
        print(f"[Redis] Respuesta del job {job_id} guardada en {key}")
    except Exception as e:
        print(f"Error guardando respuesta: {e}")

def get_cronjob_responses(job_id: str):
    keys = r.keys(f"cronjob_response:{job_id}:*")
    responses = []
    for k in keys:
        data = r.get(k)
        try:
            response = json.loads(data)
            responses.append({
                "timestamp": k.split(":")[-1],
                "data": response
            })
        except json.JSONDecodeError:
            print(f"Error decodificando respuesta en clave {k}")
    
    # Ordenar por timestamp (más reciente primero)
    responses.sort(key=lambda x: x["timestamp"], reverse=True)
    return responses

def update_cronjob_status(job_id: str, paused: bool):
    job = get_cronjob(job_id)
    if job is not None:
        job["paused"] = paused
        save_cronjob(job_id, job)
        print(f"[Redis] Estado del job {job_id} actualizado a {'pausado' if paused else 'activo'}")
    else:
        print(f"[CronManager] El trabajo con ID {job_id} no existe en Redis.")