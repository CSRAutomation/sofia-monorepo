# Usa una imagen base oficial de Python
FROM python:3.10-slim

# Establece el directorio de trabajo en el contenedor
WORKDIR /app

# El contexto de build en cloudbuild.yaml es la raíz del monorepo.
# Esto nos permite copiar carpetas compartidas como `libs/` si fuera necesario.
# COPY libs/ /app/libs/

# Copia el código específico del servicio `agent-sofia` al contenedor
COPY services/agent-sofia/ /app/

# Instala las dependencias de Python
# Usar --no-cache-dir reduce el tamaño de la imagen
RUN pip install --no-cache-dir -r requirements.txt

# Cloud Run proporciona la variable de entorno PORT.
# La función `run` de ADK la usa automáticamente.
EXPOSE 8080

# Comando para ejecutar el agente cuando se inicie el contenedor.
CMD ["python", "main.py"]