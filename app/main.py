from fastapi import FastAPI, HTTPException
from uuid import uuid4
import redis_manager, scheduler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict
app = FastAPI()


# Crear el modelo para los datos de CronJob
class CronJob(BaseModel):
    name: str
    script_path: Dict[str, str]  # Asegúrate de que esto sea un diccionario
    interval_seconds: int

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

# Cambiar la función para aceptar un objeto CronJob
@app.post("/cronjob/")
def create_cronjob(cronjob: CronJob):
    job_id = str(uuid4())
    job = {
        "id": job_id,
        "name": cronjob.name,
        "script_path": cronjob.script_path,
        "interval_seconds": cronjob.interval_seconds
    }
    redis_manager.save_cronjob(job_id, job)
    scheduler.add_cronjob_to_scheduler(job_id, cronjob.script_path["url"], cronjob.interval_seconds)
    return job

@app.get("/cronjob/")
def list_jobs():
    return redis_manager.get_all_cronjobs()

@app.get("/run/{job_id}")
def run_now(job_id: str):
    job = redis_manager.get_cronjob(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        response = scheduler.run_script(job["script_path"]["url"])
        if response is None:
            response = "No output from the script"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el script: {str(e)}")

    # Verifica que la respuesta no sea None
    if response is not None:
        redis_manager.save_cronjob_response(job_id, response)
    else:
        raise HTTPException(status_code=500, detail="La respuesta del cronjob es inválida.")
    
    return {"message": f"{job['name']} ejecutado manualmente", "response": response}

# En el script del cronjob


@app.delete("/cronjob/{job_id}")
def delete_job(job_id: str):
    scheduler.scheduler.remove_job(job_id)
    redis_manager.delete_cronjob(job_id)
    return {"message": "Eliminado"}

@app.get("/cronjob/{job_id}/responses")
def get_cronjob_responses(job_id: str):
    return redis_manager.get_cronjob_responses(job_id)