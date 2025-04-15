# Usar una imagen base ligera de Python
FROM python:3.12-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar virtualenv
RUN pip install --no-cache-dir virtualenv

# Crear un entorno virtual fuera del código
RUN python -m venv /venv

# Actualizar pip del entorno virtual
RUN /venv/bin/pip install --upgrade pip

# Copiar requerimientos
COPY requirements.txt .

# Instalar dependencias en el venv
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Copiar el código fuente
COPY ./app /app

# Exponer el nuevo puerto de FastAPI
EXPOSE 8001

# Usar el entorno virtual para ejecutar Uvicorn en puerto 8001
CMD ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--reload-dir", "/app"]
