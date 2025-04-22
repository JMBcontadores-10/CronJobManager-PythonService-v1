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


# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambia esto al origen de tu frontend
    allow_credentials=True,
    allow_methods=["*"],  # Métodos permitidos (GET, POST, etc.)
    allow_headers=["*"],  # Headers permitidos
)

# Crear el modelo para los datos de CronJob
class CronJob(BaseModel):
    name: str
    script_path: Dict[str, str]  # Debería ser un diccionario con una clave "url"
    interval_seconds: int
    paused: bool = False  # Agregar el atributo paused

    def toggle(self):
        self.paused = not self.paused
        self.is_active = not self.paused  # Si está pausado, no está activo

# Evento de startup para conectar a Redis y cargar los trabajos
@app.on_event("startup")
async def startup_event():
    global redis_conn
    redis_conn = await start_redis()  # Espera hasta que Redis esté disponible
    if not redis_conn:
        print("[Startup] No se pudo conectar a Redis. Continuando sin conexión.")
        return  # Si no hay conexión a Redis, termina el evento de inicio

    redis_manager.connect_to_redis()

    print("[CronManager] Cargando trabajos desde Redis...")
    jobs = redis_manager.get_all_cronjobs()
    for job in jobs:
        if 'paused' not in job:
            job['paused'] = False
        redis_manager.save_cronjob(job['id'], job)  # Guardar el estado actualizado

    # Cargar los trabajos al scheduler después de haber verificado que todos estén pausados si es necesario
    scheduler.load_jobs_from_redis()

    print("[CronManager] Verificando estado del scheduler...")
    if not scheduler.scheduler.running:
        print("[CronManager] Iniciando el scheduler...")
        scheduler.start()
        print("[CronManager] Scheduler iniciado correctamente.")
    else:
        print("[CronManager] El scheduler ya está en ejecución.")
    
    # Verificar que los trabajos se hayan cargado correctamente
    job_count = len(scheduler.scheduler.get_jobs())
    print(f"[CronManager] Total de trabajos activos en el scheduler: {job_count}")
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

@app.get("/cronjob/")
def list_jobs():
    jobs = redis_manager.get_all_cronjobs()
    for job in jobs:
        job['is_active'] = not job.get("paused", False)  # Si está pausado, no está activo
    return jobs

# Crear un nuevo cronjob
@app.post("/cronjob/")
def create_cronjob(cronjob: CronJob):
    try:
        print(f"[CronManager] Creando nuevo cronjob: {cronjob.name}")
        job_id = str(uuid4())
        job = {
            "id": job_id,
            "name": cronjob.name,
            "script_path": cronjob.script_path,
            "interval_seconds": cronjob.interval_seconds,
            "paused": cronjob.paused
        }
        redis_manager.save_cronjob(job_id, job)
        
        # Si el trabajo no está pausado, añadirlo al scheduler
        if not cronjob.paused:
            print(f"[CronManager] Añadiendo job {job_id} al scheduler (no está pausado)")
            scheduler.add_cronjob_to_scheduler(job_id, cronjob.script_path, cronjob.interval_seconds)
        else:
            print(f"[CronManager] Job {job_id} está pausado, no se añade al scheduler")
        
        return job
    except ValueError as e:
        print(f"[CronManager] Error al crear cronjob: {str(e)}")
        raise HTTPException(status_code=422, detail=f"Error de validación: {str(e)}")
    except Exception as e:
        print(f"[CronManager] Error inesperado al crear cronjob: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error inesperado: {str(e)}")
    
@app.get("/run/{job_id}")
def run_now(job_id: str):
    job = redis_manager.get_cronjob(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    try:
        # Asegúrate de añadir el job_id al script_path antes de ejecutarlo
        script_path = job["script_path"]
        script_path["job_id"] = job_id
        
        response = scheduler.run_script(script_path)
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

# Eliminar un cronjob
@app.delete("/cronjob/{job_id}")
def delete_job(job_id: str):
    # Primero, eliminamos el cronjob de Redis
    redis_manager.delete_cronjob(job_id)
    
    # Luego, verificamos si el trabajo existe en el scheduler antes de intentar eliminarlo
    job = scheduler.scheduler.get_job(job_id)
    if job:
        scheduler.scheduler.remove_job(job_id)
        return {"message": "Cronjob eliminado con éxito"}
    else:
        # Si el cronjob no existe, simplemente devolvemos un mensaje indicando que no se encontró
        return {"message": "Cronjob no encontrado, no se realizó ninguna acción"}

@app.get("/cronjob/{job_id}/responses")
def get_cronjob_responses(job_id: str):
    return redis_manager.get_cronjob_responses(job_id)

# Pausar un cronjob
@app.post("/cronjob/{job_id}/pause")
def pause_job(job_id: str):
    try:
        scheduler.scheduler.pause_job(job_id)
        redis_manager.update_cronjob_status(job_id, True)
        return {"message": f"Job {job_id} pausado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo pausar el job: {str(e)}")

# Reanudar un cronjob
@app.post("/cronjob/{job_id}/resume")
def resume_job(job_id: str):
    try:
        scheduler.scheduler.resume_job(job_id)
        redis_manager.update_cronjob_status(job_id, False)
        return {"message": f"Job {job_id} reanudado"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo reanudar el job: {str(e)}")

@app.post("/cronjob/{job_id}/toggle")
def toggle_job(job_id: str):
    try:
        # Intentamos obtener el cronjob desde Redis
        job = redis_manager.get_cronjob(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado en Redis")

        # Verificamos si el job está en el scheduler antes de intentar pausarlo
        existing_job = scheduler.scheduler.get_job(job_id)
        if not existing_job:
            # Si el trabajo no existe en el scheduler pero sí en Redis, lo agregamos
            if not job["paused"]:
                scheduler.add_cronjob_to_scheduler(job_id, job["script_path"], job["interval_seconds"])
                existing_job = scheduler.scheduler.get_job(job_id)
                if not existing_job:
                    raise HTTPException(status_code=500, detail=f"No se pudo crear el job {job_id} en el scheduler")

        # Alternamos el estado de "paused"
        new_state = not job["paused"]
        job["paused"] = new_state
        redis_manager.update_cronjob_status(job_id, new_state)

        # Intentamos pausar o reanudar el trabajo en el scheduler
        if new_state:
            scheduler.scheduler.pause_job(job_id)
        else:
            scheduler.scheduler.resume_job(job_id)

        return {"message": f"Job {job_id} {'pausado' if new_state else 'reanudado'}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al alternar el estado del cronjob: {str(e)}")