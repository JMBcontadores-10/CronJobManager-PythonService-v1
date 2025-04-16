# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo requirements.txt al contenedor
COPY requirements.txt .

# Instala las dependencias desde requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Crea un entorno virtual dentro del contenedor
RUN python -m venv /venv

# Activa el entorno virtual y instala las dependencias dentro de él
RUN /venv/bin/pip install --no-cache-dir -r requirements.txt

# Copia todo el contenido de la carpeta app al contenedor
COPY app /app

# Expone el puerto 8000
EXPOSE 8000

# Define el comando para ejecutar la aplicación FastAPI con Uvicorn usando el entorno virtual
CMD ["/venv/bin/uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "/app"]
