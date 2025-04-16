import redis
import json
r = redis.Redis(host="172.22.82.26", port=6379, decode_responses=True)
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