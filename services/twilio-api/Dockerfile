# Usa una imagen base de Python oficial.
FROM python:3.11-slim

# Establece el directorio de trabajo en /app
WORKDIR /app

# Copia el archivo de requerimientos
COPY requirements.txt .

# Instala las dependencias.
RUN pip install --no-cache-dir -r requirements.txt

# Copia el código fuente del servicio al contenedor.
COPY . .

# Expone el puerto en el que la aplicación se ejecutará.
EXPOSE 8080


# Comando para ejecutar la aplicación usando Gunicorn.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]