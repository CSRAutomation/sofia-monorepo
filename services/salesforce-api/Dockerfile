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
COPY . .


# Comando para ejecutar la aplicación usando Gunicorn, el servidor WSGI.
# app:app: Le dice a Gunicorn que cargue el objeto 'app' desde el archivo 'app.py'.
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:$PORT --workers ${WORKERS:-4} --threads 8 --timeout 120 app:app"]