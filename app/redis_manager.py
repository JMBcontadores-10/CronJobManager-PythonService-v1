import redis
import json
r = redis.Redis(host="172.22.82.26", port=6379, db=2, decode_responses=True)
def save_cronjob(job_id: str, data: dict):
    r.set(f"cronjob:{job_id}", json.dumps(data))

def get_cronjob(job_id: str):
    data = r.get(f"cronjob:{job_id}")
    return json.loads(data) if data else None

def get_all_cronjobs():
    keys = r.keys("cronjob:*")
    return [json.loads(r.get(k)) for k in keys]

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