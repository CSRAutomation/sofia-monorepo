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
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]