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
# Usamos Gunicorn, un servidor WSGI de nivel de producción, para ejecutar la aplicación Flask.
# --bind 0.0.0.0:$PORT: Escucha en todas las interfaces de red en el puerto que Cloud Run asigna.
# --workers ${WORKERS:-4}: Lanza 4 procesos de trabajo (o los que se definan en la variable WORKERS) para manejar peticiones en paralelo.
# --threads 8: Permite a cada worker manejar hasta 8 peticiones concurrentes que estén esperando por I/O (ej. llamadas a otras APIs).
# --timeout 120: Da a cada petición hasta 120 segundos para completarse, evitando que Gunicorn la cancele prematuramente.
# app:app: Le dice a Gunicorn que cargue el objeto 'app' desde el archivo 'app.py'.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers ${WORKERS:-4} --threads 8 --timeout 120 app:app"]