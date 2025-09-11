# Usa una imagen base oficial de Python
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos
COPY requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación
COPY . .

# Expone el puerto 8080 para que Cloud Run pueda conectarse
EXPOSE 8080

# Comando para iniciar la aplicación con Gunicorn, el servidor WSGI recomendado para producción.
# Gunicorn gestionará los workers de Uvicorn para un rendimiento y estabilidad óptimos.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers ${WORKERS:-4} --threads 8 --timeout 120 app:app"]