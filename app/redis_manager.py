import redis
import json
r = redis.Redis(host="172.22.82.26", port=6379, db=2, decode_responses=True)

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
    return jobs


def delete_cronjob(job_id: str):
    r.delete(f"cronjob:{job_id}")
def save_cronjob_response(job_id: str, response: str):
    r.set(f"cronjob_response:{job_id}", response)


def get_cronjob_responses(job_id):
    prefix = f"cronmanager_crons:{job_id}:"
    keys = r.keys(f"{prefix}*")
    responses = []

    for key in sorted(keys):
        timestamp = key.split(":")[-1]
        data = r.get(key)
        try:
            data_json = json.loads(data)
        except Exception:
            data_json = data  # Si no es JSON válido, lo dejamos como texto
        responses.append({
            "timestamp": timestamp,
            "response": data_json
        })
    return responses


def update_cronjob_status(job_id: str, paused: bool):
    job = get_cronjob(job_id)
    if job is not None:
        job["paused"] = paused
        save_cronjob(job_id, job)
    else:
        print(f"[CronManager] El trabajo con ID {job_id} no existe en Redis.")
