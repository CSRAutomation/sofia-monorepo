# Usar una imagen base oficial de Python, ligera y segura.
FROM python:3.12-slim


# Establecer variables de entorno para Python que mejoran el rendimiento en contenedores.
ENV PYTHONDONTWRITEBYTECODE 1

ENV PYTHONUNBUFFERED 1
# Añadir la raíz del proyecto al PYTHONPATH para permitir importaciones desde libs/

ENV PYTHONPATH /app

# Establecer el directorio de trabajo en el contenedor.
WORKDIR /app

# Copiar el archivo de dependencias del servicio específico e instalar.

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el monorepo al contenedor.
# Esto permite que el servicio acceda a las librerías compartidas en libs/
COPY . .

# Comando para ejecutar la aplicación usando Gunicorn, el servidor WSGI de producción.
# --bind 0.0.0.0:8080 : Escucha en todas las interfaces en el puerto 8080, que es el que Cloud Run espera.
# --workers 1 : Un solo proceso de trabajo, adecuado para el entorno de 1 vCPU de Cloud Run.
# --threads 8 : Múltiples hilos para manejar peticiones concurrentes.
# --timeout 0 : Deshabilita el timeout de Gunicorn para que Cloud Run maneje los timeouts de las peticiones.
# services.salesforce-api.app:app : Le dice a Gunicorn que busque el objeto 'app' (el de Flask)
# en el módulo Python 'services.salesforce-api.app'.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "services.salesforce-api.app:app"]