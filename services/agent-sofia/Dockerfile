# Usa una imagen base oficial de Python
FROM python:3.12-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos
COPY requirements.txt .

# Instala las dependencias de Python
# La opción --no-cache-dir es una buena práctica para mantener la imagen ligera
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de la aplicación
COPY . .

# Expone el puerto 8080 para que Cloud Run pueda conectarse
EXPOSE 8080

# Comando para ejecutar la aplicación cuando el contenedor se inicie
# Usa Gunicorn, un servidor de producción robusto que ya tienes en tus dependencias
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]