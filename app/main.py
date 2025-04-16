from fastapi import FastAPI
from uuid import uuid4
import redis_manager, scheduler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "¡Hola, CronManager activo!"}
@app.get("/vista")
def mostrar_vista():
    return FileResponse("templates/index.html")

@app.on_event("startup")
def startup_event():
    scheduler.load_jobs_from_redis()
    scheduler.start()

@app.post("/cronjob/")
def create_cronjob(name: str, script_path: str, interval_seconds: int):
    job_id = str(uuid4())
    job = {
        "id": job_id,
        "name": name,
        "script_path": script_path,
        "interval_seconds": interval_seconds
    }
    redis_manager.save_cronjob(job_id, job)
    scheduler.add_cronjob_to_scheduler(job_id, script_path, interval_seconds)
    return job

@app.get("/cronjob/")
def list_jobs():
    return redis_manager.get_all_cronjobs()

@app.get("/run/{job_id}")
def run_now(job_id: str):
    job = redis_manager.get_cronjob(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    scheduler.run_script(job["script_path"])
    return {"message": f"{job['name']} ejecutado manualmente"}

@app.delete("/cronjob/{job_id}")
def delete_job(job_id: str):
    scheduler.scheduler.remove_job(job_id)
    redis_manager.delete_cronjob(job_id)
    return {"message": "Eliminado"}

