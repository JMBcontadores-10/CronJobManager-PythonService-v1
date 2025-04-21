from fastapi import FastAPI, HTTPException
from uuid import uuid4
import redis_manager, scheduler
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict
from config import start_redis
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Lista de orígenes permitidos (agrega los que necesites)

# Agregar el middleware de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # Orígenes permitidos
    allow_credentials=True,
    allow_methods=["*"],              # Métodos permitidos (GET, POST, etc.)
    allow_headers=["*"],              # Headers permitidos
)

# Crear el modelo para los datos de CronJob
class CronJob(BaseModel):
    name: str
    script_path: Dict[str, str]  # Debería ser un diccionario con una clave "url"
    interval_seconds: int

app = FastAPI()

### al iniciar la app nos conectamos a redis y cargamos los jobs
@app.on_event("startup")
async def startup_event():
    global redis_conn
    redis_conn = await start_redis()
    if not redis_conn:
        print("[Startup] No se pudo conectar a Redis. Continuando sin conexión.")
    redis_manager.connect_to_redis()
    print("[CronManager] Cargando trabajos desde Redis...")
    scheduler.load_jobs_from_redis()
    print("[CronManager] Iniciando el scheduler...")
    if not scheduler.scheduler.running:
        scheduler.start()
        print("[CronManager] Listo.")

@app.get("/status")
def status():
    try:
        redis_manager.r.ping()
        return {"status": "ok", "redis": "connected"}
    except:
        return {"status": "ok", "redis": "not connected"}

@app.get("/")
def read_root():
    return {"message": "¡Hola, CronManager activo!"}

@app.get("/vista")
def mostrar_vista():
    return FileResponse("templates/index.html")



# Cambiar la función para aceptar un objeto CronJob
@app.post("/cronjob/")
def create_cronjob(cronjob: CronJob):
    try:
        print(cronjob)  # Esto muestra el contenido del objeto CronJob recibido
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
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Error de validación: {str(e)}")

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
            response = {"message": "No output from the script"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al ejecutar el script: {str(e)}")

    # Verifica que la respuesta no sea None
    if response and response != "No output from the script":
        redis_manager.save_cronjob_response(job_id, response)
    else:
        response = {"message": "No output from the script"}

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

@app.post("/cronjob/{job_id}/pause")
def pause_job(job_id: str):
    try:
        scheduler.scheduler.pause_job(job_id)
        redis_manager.update_cronjob_status(job_id, True)
        return {"message": f"Job {job_id} pausado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo pausar el job: {str(e)}")

@app.post("/cronjob/{job_id}/resume")
def resume_job(job_id: str):
    try:
        scheduler.scheduler.resume_job(job_id)
        redis_manager.update_cronjob_status(job_id, False)
        return {"message": f"Job {job_id} reanudado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo reanudar el job: {str(e)}")