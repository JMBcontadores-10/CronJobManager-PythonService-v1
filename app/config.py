import os
from dotenv import load_dotenv
import redis.asyncio as aioredis
from motor.motor_asyncio import AsyncIOMotorClient
import aiomysql
import json
import asyncio
from pathlib import Path

env_path = Path(__file__).resolve().parent.parent
load_dotenv()

# REDIS
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# MONGO
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "cronmanager")

# MYSQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "cronmanager")

# BACKENDS
CRON_STORAGE_BACKEND = os.getenv("CRON_STORAGE_BACKEND", "redis")
LOG_STORAGE_BACKEND = os.getenv("LOG_STORAGE_BACKEND", "mongo")
ENDPOINT_CONFIG_STORAGE_BACKEND = os.getenv("ENDPOINT_CONFIG_STORAGE_BACKEND", "mongo")

# Nombres
CRON_STORAGE_NAME = os.getenv("CRON_STORAGE_NAME", "crons")
LOG_STORAGE_NAME = os.getenv("LOG_STORAGE_NAME", "cron_logs")
ENDPOINT_CONFIG_NAME = os.getenv("ENDPOINT_CONFIG_NAME", "endpoints_config")

# Fallback file
CRON_LOG_FILE = os.getenv("CRON_LOG_FILE", "crons_file.log")
APP_LOG_FILE = os.getenv("APP_LOG_FILE", "logs_file.log")
ENDPOINT_CONFIG_FILE = os.getenv("ENDPOINT_CONFIG_FILE", "endpoints_config.log")


# ========== REDIS ==========
async def start_redis(attempts=3):
    try:
        redis_client = aioredis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        await redis_client.ping()
        print("[Redis] Conexión exitosa.")
        return redis_client
    except Exception as e:
        if attempts > 1:
            print(f"[Redis] Error de conexión: {e}")
            print(f"[Redis] Reintentando conexión en 5 segundos... Intentos restantes: {attempts - 1}")
            await asyncio.sleep(5)
            return await start_redis(attempts - 1)  # Reintentar conexión
        else:
            print("[Redis] Error de conexión: No se pudo conectar después de 3 intentos.")
            return None


# ========== MONGO ==========
async def start_mongodb():
    try:
        client = AsyncIOMotorClient(MONGO_URI)
        db = client[MONGO_DB_NAME]
        print("[MongoDB] Conexión exitosa.")
        return db
    except Exception as e:
        print(f"[MongoDB] Error de conexión: {e}")
        return None


# ========== MYSQL ==========
async def start_mysql():
    try:
        conn = await aiomysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            db=MYSQL_DB,
            autocommit=True
        )
        print("[MySQL] Conexión exitosa.")
        return conn
    except Exception as e:
        print(f"[MySQL] Error de conexión: {e}")
        return None


# ========== FILE STORAGE ==========
class FileStorage:
    def __init__(self, filename):
        self.filename = filename
        # Crea el archivo si no existe
        try:
            open(self.filename, "a").close()
        except Exception as e:
            print(f"[FileStorage] Error inicializando archivo: {e}")

    async def save(self, data):
        try:
            with open(self.filename, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            print(f"[FileStorage] Error guardando datos: {e}")

    async def get_all(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                return [json.loads(line) for line in f.readlines()]
        except Exception as e:
            print(f"[FileStorage] Error leyendo archivo: {e}")
            return []


# ========== FACTORY DE ALMACENAMIENTO ==========
async def get_storage(backend_type: str, fallback_file: str, resource_name: str):
    backend = backend_type.lower()
    conn = None

    if backend == "redis":
        conn = await start_redis()
    elif backend == "mongo":
        db = await start_mongodb()
        conn = db[resource_name] if db else None
    elif backend == "mysql":
        conn = await start_mysql()
        if conn:
            conn._table_name = resource_name  # puedes usarlo en funciones personalizadas
    elif backend == "file":
        conn = FileStorage(fallback_file)
    else:
        print(f"[Config] BACKEND '{backend}' no soportado, usando archivo.")
        conn = FileStorage(fallback_file)

    if conn is None:
        print(f"[Config] No se pudo conectar a '{backend}', usando archivo.")
        conn = FileStorage(fallback_file)

    return conn


# ========== FUNCIONES DE ACCESO ESPECÍFICO ==========
async def get_cron_storage():
    return await get_storage(CRON_STORAGE_BACKEND, CRON_LOG_FILE, CRON_STORAGE_NAME)

async def get_log_storage():
    return await get_storage(LOG_STORAGE_BACKEND, APP_LOG_FILE, LOG_STORAGE_NAME)

async def get_endpoint_config_storage():
    return await get_storage(ENDPOINT_CONFIG_STORAGE_BACKEND, ENDPOINT_CONFIG_FILE, ENDPOINT_CONFIG_NAME)
