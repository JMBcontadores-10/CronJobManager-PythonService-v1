import os

def capitalize_and_clean_folder_name(name):
    """Convierte el nombre de la carpeta a formato Capitalizado y elimina espacios."""
    name = name.strip().replace(" ", "")
    return name.title()

def create_structure(base_folder, module_name):
    """Crea la estructura de carpetas y archivos para un módulo específico."""
    module_name_cleaned = capitalize_and_clean_folder_name(module_name)
    module_path = os.path.join(base_folder, module_name_cleaned)
    
    # Verificar si el módulo ya existe
    if os.path.exists(module_path):
        print(f"El módulo '{module_name_cleaned}' ya existe. Elija otro nombre.")
        return False  # No continúa si el módulo ya existe
    
    # Crear la carpeta principal del módulo
    os.makedirs(module_path)
    
    # Crear las subcarpetas api, models, repositories, services, validations, exports, utils
    subfolders = ["api", "models", "repositories", "services", "validations", "exports", "utils"]
    for subfolder in subfolders:
        subfolder_path = os.path.join(module_path, subfolder)
        os.makedirs(subfolder_path)
        
        # Crear __init__.py para permitir la importación
        with open(os.path.join(subfolder_path, "__init__.py"), "w") as f:
            # Para las carpetas que tienen subcomponentes, agregamos imports relativos
            if subfolder == "validations":
                f.write(f"from .user_validation import validate_user_data\n")
                f.write(f"from .email_validation import validate_email_format\n")
            elif subfolder == "repositories":
                f.write(f"from .main_users_repository import create_user\n")
            elif subfolder == "services":
                f.write(f"from .main_user_service import register_user\n")
            elif subfolder == "models":
                f.write(f"from .user_models import UserCreateRequest, UserResponse\n")

    # Crear el archivo __init__.py en la raíz del módulo
    with open(os.path.join(module_path, "__init__.py"), "w") as f:
        pass
    
    # Crear los archivos de ejemplo para las rutas, servicios, repositorios, etc.
    create_example_files(module_path, module_name_cleaned)

    return True  # Indica que se creó correctamente la estructura

def create_example_files(module_path, module_name):
    """Crea los archivos de ejemplo como routes.py, main_user_service.py, etc."""
    # Comentario de la ruta de archivo: api/routes.py
    api_folder = os.path.join(module_path, "api")
    with open(os.path.join(api_folder, "routes.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/api/routes.py

from fastapi import APIRouter
from {module_name}.models.user_models import UserCreateRequest
from {module_name}.services.main_user_service import register_user
from {module_name}.validations import validate_user_data, validate_email_format

router = APIRouter()

@router.post("/create")
async def create_user_endpoint(user: UserCreateRequest):
    await validate_user_data(user)
    await validate_email_format(user)
    user_data = await register_user(user)
    return user_data    

@router.get("/hola")
async def hello_user():
    return {{"message": "Hola, mundo!"}}
""")

    # Comentario de la ruta de archivo: repositories/main_users_repository.py
    repositories_folder = os.path.join(module_path, "repositories")
    with open(os.path.join(repositories_folder, "main_users_repository.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/repositories/main_users_repository.py

from config import get_database, logger
from {module_name}.models.user_models import UserCreateRequest
from motor.motor_asyncio import AsyncIOMotorCollection

async def get_users_collection() -> AsyncIOMotorCollection:
    db = get_database("{module_name.lower()}_db")
    collection = db.get_collection("{module_name.lower()}_users")
    try:
        await collection.find_one()
    except CollectionInvalid:
        print("Colección '{module_name.lower()}_users' no existe, creando...")
        await db.create_collection("{module_name.lower()}_users")
    return collection

async def create_user(user: UserCreateRequest):
    collection = await get_users_collection()
    logger.info("Se creó el usuario.")
    result = await collection.insert_one(user.dict())
    return str(result.inserted_id)
""")

    # Comentario de la ruta de archivo: services/main_user_service.py
    services_folder = os.path.join(module_path, "services")
    with open(os.path.join(services_folder, "main_user_service.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/services/main_user_service.py

from {module_name}.repositories.main_users_repository import create_user
from {module_name}.models.user_models import UserCreateRequest

async def register_user(user_data: UserCreateRequest):
    user_id = await create_user(user_data)
    return user_id
""")

    # Comentario de la ruta de archivo: validations/email_validation.py
    validations_folder = os.path.join(module_path, "validations")
    with open(os.path.join(validations_folder, "email_validation.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/validations/email_validation.py

from fastapi import HTTPException
from {module_name}.models.user_models import UserCreateRequest

async def validate_email_format(user: UserCreateRequest):
    if "@" not in user.email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    return user
""")

    with open(os.path.join(validations_folder, "user_validation.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/validations/user_validation.py

from fastapi import HTTPException
from {module_name}.models.user_models import UserCreateRequest

async def validate_user_data(user: UserCreateRequest):
    if not user.name:
        raise HTTPException(status_code=400, detail="Name is required")
    if "juan" in user.name.lower():
        raise HTTPException(status_code=400, detail="Name cannot contain 'Juan'")
    return user
""")

    # Comentario de la ruta de archivo: models/user_models.py
    models_folder = os.path.join(module_path, "models")
    with open(os.path.join(models_folder, "user_models.py"), "w") as f:
        f.write(f"""# Ruta: {module_name}/models/user_models.py

from pydantic import BaseModel

class UserCreateRequest(BaseModel):
    name: str
    email: str
    age: int

class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    age: int
""")

    # Carpeta utils vacía
    utils_folder = os.path.join(module_path, "utils")
    with open(os.path.join(utils_folder, "__init__.py"), "w") as f:
        pass

def main():
    base_folder = "."  # Define la carpeta principal donde se creará el módulo (en este caso, se usa el directorio actual)
    module_name = input("Ingrese el nombre del módulo: ")  # Permite ingresar el nombre del módulo
    if create_structure(base_folder, module_name):
        update_main_py(module_name)
        print(f"Estructura para el módulo {module_name} creada con éxito.")
        # Genera la documentación para el módulo
        generate_md_documentation(module_name)
        print(f"Documentación generada para el módulo {module_name}.")
    
    print("Reiniciando docker")
    run_docker_compose()
    print("Docker se reinicio")
    
def update_main_py(module_name):
    """Actualiza el archivo main.py con la importación de las rutas del nuevo módulo."""
    main_file_path = "main.py"
    module_name_lower = module_name.lower()
    prefix = f'/{module_name.title()}/v1'  # Esto se ajusta según el nombre capitalizado del módulo
    module_name_cleaned = module_name.lower().replace(' ', '')

    with open(main_file_path, "a") as f:
        cleaned_module_name = module_name.replace(' ', '').capitalize()  # Quita los espacios y pone la primera letra en mayúscula
        f.write(f"\nfrom {cleaned_module_name}.api.routes import router as {cleaned_module_name.lower()}_router")
        f.write(f"\napp.include_router({cleaned_module_name.lower()}_router, prefix='/{cleaned_module_name.lower()}/v1', tags=['{cleaned_module_name.lower()}'])")


def run_docker_compose():
    """Ejecuta los comandos docker-compose."""
    os.system('sudo docker-compose down')
    os.system('sudo docker-compose up --build')
    
    
def generate_md_documentation(module_name):
    """Genera el archivo README.md con la documentación básica del módulo, descripción y enlace a diagrama."""
    module_name_cleaned = capitalize_and_clean_folder_name(module_name)
    module_path = os.path.join(".", module_name_cleaned)

    # Verifica si el módulo existe
    if not os.path.exists(module_path):
        print(f"El módulo '{module_name_cleaned}' no existe.")
        return False
    
    # Ruta del archivo README.md
    readme_path = os.path.join(module_path, "README.md")
    
    # Crea o actualiza el archivo README.md
    with open(readme_path, "w") as f:
        f.write(f"# {module_name_cleaned} Module Documentation\n\n")
        
        # Descripción del módulo
        f.write(f"## Descripción del Módulo\n")
        f.write(f"Este módulo maneja las funcionalidades relacionadas con {module_name_cleaned.lower()}. Aquí puedes describir en detalle la finalidad, los casos de uso y la lógica de negocio del módulo. ¿Qué resuelve este módulo? ¿Cómo se integra con otros módulos del sistema?\n\n")
        
        # Enlace al diagrama
        f.write(f"## Diagrama de Arquitectura\n")
        f.write(f"Adjunta un enlace al diagrama de la arquitectura del módulo. Puedes usar Excalidraw, Lucidchart, o cualquier otra herramienta de diagramas. Por ejemplo, puedes pegar aquí el enlace del diagrama generado en Excalidraw:\n")
        f.write(f"[Diagrama de Arquitectura del Módulo](https://excalidraw.com/#json=TU_DIAGRAMA_LINK)\n\n")

        # Estructura de Carpetas
        f.write(f"## Estructura de Carpetas\n")
        f.write(f"El módulo sigue la siguiente estructura de carpetas:\n")
        f.write(f"- `api/`: Contiene las rutas y controladores.\n")
        f.write(f"- `models/`: Define los modelos de datos.\n")
        f.write(f"- `repositories/`: Contiene las funciones de acceso a datos.\n")
        f.write(f"- `services/`: Contiene los servicios que procesan la lógica del negocio.\n")
        f.write(f"- `validations/`: Funciones de validación de datos de entrada.\n")
        f.write(f"- `exports/`: Archivos relacionados con la exportación de datos.\n")
        f.write(f"- `utils/`: Funciones utilitarias para el módulo.\n\n")
        
        # Rutas API
        f.write(f"## Rutas API\n")
        f.write(f"Las siguientes rutas están disponibles en este módulo:\n")
        f.write(f"1. `POST /{module_name_cleaned.lower()}/v1/create`: Crea un nuevo usuario.\n")
        f.write(f"2. `GET /{module_name_cleaned.lower()}/v1/hola`: Devuelve un mensaje de saludo.\n\n")
        
        # Servicios
        f.write(f"## Servicios\n")
        f.write(f"Este módulo proporciona los siguientes servicios:\n")
        f.write(f"- `register_user`: Registra un nuevo usuario en el sistema.\n\n")
        
        # Repositorios
        f.write(f"## Repositorios\n")
        f.write(f"El módulo interactúa con la base de datos a través del repositorio `main_users_repository`.\n")
        f.write(f"Este repositorio maneja la creación y obtención de usuarios.\n")

    print(f"Documentación generada en: {readme_path}")
    return True

    
if __name__ == "__main__":
    main()
