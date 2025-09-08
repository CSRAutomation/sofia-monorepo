 # Documentación Técnica: Agente de IA "Sofia"
 
 Este documento describe la arquitectura y funcionalidades del **Agente Sofia**, un servicio de inteligencia artificial conversacional. Su finalidad principal es **mejorar e innovar la atención al servicio al cliente**, proporcionando respuestas rápidas, precisas y contextuales.
 
 ## 1. Descripción General del Agente
 
 El Agente Sofia es una aplicación construida sobre el framework `FastAPI` y el **Agent Development Kit (ADK)** de Google, diseñada para ser desplegada como un servicio web contenedorizado en Google Cloud Run.
 
 Utiliza un modelo de lenguaje grande (LLM) de Google (Gemini) para comprender las solicitudes de los usuarios, mantener conversaciones fluidas y ejecutar tareas específicas a través de herramientas externas. El objetivo es automatizar consultas comunes y resolver problemas de manera eficiente.
 
 ## 2. Estructura del Proyecto
 
 El proyecto sigue la estructura estándar definida por el ADK:
 
 ```
 /agent-sofia/
 ├── agent/
 │   ├── agent.yaml      # Configuración principal del agente (prompt, herramientas, modelo).
 │   └── tools/
 │       └── tool_script.py # Implementación de las herramientas en Python.
 ├── main.py             # Punto de entrada de la aplicación FastAPI.
 ├── Dockerfile          # Instrucciones para construir la imagen del contenedor.
 ├── requirements.txt    # Dependencias de Python.
 └── .env                # (Opcional) Variables de entorno locales.
 ```
 
 ## 3. Configuración del Agente (`agent/agent.yaml`)
 
 Este archivo es el cerebro del agente. Define su comportamiento, capacidades y las herramientas que puede utilizar.
 
 -   **`instructions`**: Define el **prompt del sistema**. Es el conjunto de directivas que establecen la personalidad de Sofia, su tono amable y servicial, las tareas que puede realizar y las reglas que debe seguir para interactuar con los clientes.
 -   **`model`**: Especifica el modelo de lenguaje a utilizar (ej. `gemini-2.0-flash`).
 -   **`tools`**: Lista las herramientas que el agente tiene a su disposición. Cada entrada se corresponde con una función de Python definida en el directorio `tools/`.
 
 ## 4. Herramientas (`agent/tools/`)
 
 Las herramientas son funciones de Python que le otorgan a Sofia capacidades para interactuar con sistemas externos y realizar acciones concretas. Esto le permite ir más allá de una simple conversación y resolver problemas reales de los clientes.
 
 ### Funciones Implementadas y Logros:
 
 -   **`consultar_estado_pedido(id_pedido: str)`**:
     -   **¿Qué hace?**: Se conecta al sistema de gestión de pedidos para obtener el estado actual de un pedido específico.
     -   **¿Qué logramos?**: Permite a los clientes auto-servirse para conocer el estado de su compra en tiempo real (ej. "en preparación", "enviado", "entregado"), reduciendo el volumen de llamadas y tickets para el equipo de soporte.
 
 -   **`buscar_producto(nombre_producto: str)`**:
     -   **¿Qué hace?**: Realiza una búsqueda en el catálogo de productos de la empresa.
     -   **¿Qué logramos?**: Ayuda a los clientes a encontrar productos, verificar disponibilidad o recibir recomendaciones, mejorando la experiencia de compra y potenciando las ventas.
 
 -   **`registrar_caso_soporte(descripcion_problema: str, email_cliente: str)`**:
     -   **¿Qué hace?**: Crea un nuevo ticket de soporte en el sistema de CRM (ej. Zendesk, Salesforce) con la descripción del problema proporcionada por el cliente.
     -   **¿Qué logramos?**: Agiliza el proceso de creación de casos de soporte. El agente recopila la información inicial y la registra formalmente, asegurando que ningún caso se pierda y que el equipo humano reciba la información estructurada.
 
 ## 5. Punto de Entrada de la Aplicación (`main.py`)
 
 El archivo `main.py` es el componente central que **convierte a nuestro agente en una aplicación web funcional**. Actúa como el servidor donde se despliega el agente, utilizando el framework FastAPI.
 
 La función clave `get_fast_api_app` del ADK toma toda la configuración de Sofia (definida en `agent.yaml` y `tools/`) y la expone a través de puntos de conexión (endpoints) de una API RESTful.
 
 Al hacer esto, **heredamos la misma definición de rutas que se usará tanto para la interfaz de usuario de desarrollo como para la integración con Vertex AI**. Esto significa que el mismo agente puede ser probado localmente y desplegado en producción sin cambiar su lógica, garantizando consistencia y agilizando el ciclo de vida del desarrollo.
 
 ```python
 import os
 import uvicorn
 from dotenv import load_dotenv 
 from fastapi import FastAPI
 from google.adk.cli.fast_api import get_fast_api_app
 from google.cloud import logging as google_cloud_logging
 
 # Carga variables de entorno desde un archivo .env
 load_dotenv()
 
 # Configura el cliente de logging para Google Cloud
 logging_client = google_cloud_logging.Client()
 logger = logging_client.logger(__name__)
 
 # Define el directorio donde se encuentra la configuración del agente
 AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
 
 # Obtiene la URI del servicio de sesión desde las variables de entorno
 session_uri = os.getenv("SESSION_SERVICE_URI", None)
 
 # Prepara los argumentos para la creación de la app del agente
 app_args = {"agents_dir": AGENT_DIR, "web": True}
 
 # Si se proporciona una URI de sesión, la añade a los argumentos.
 # Esto es crucial para tener sesiones persistentes (ej. usando Memorystore/Redis).
 if session_uri:
     app_args["session_service_uri"] = session_uri
 else:
     # Si no, advierte que las sesiones se perderán al reiniciar el servidor.
     logger.log_text(
         "SESSION_SERVICE_URI not provided. Using in-memory session service instead. "
         "All sessions will be lost when the server restarts.",
         severity="WARNING",
     )
 
 # Crea la aplicación FastAPI usando la función del ADK
 app: FastAPI = get_fast_api_app(**app_args)
 
 app.title = "agente-sofia"
 
 # Ejecuta el servidor Uvicorn
 if __name__ == "__main__":
     # El puerto se obtiene de la variable de entorno PORT, estándar en Cloud Run.
     uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("PORT", 8080)))
 ```
 
 ### Puntos Clave de `main.py`:
 1.  **`get_fast_api_app`**: Es la función principal del ADK que construye la aplicación FastAPI, cargando la configuración del agente desde `AGENT_DIR`.
 2.  **Gestión de Sesiones**: El manejo de `SESSION_SERVICE_URI` es vital. Sin esta variable, el agente usará una memoria de sesión volátil. Para producción, se debe configurar un servicio de sesión persistente (como Redis) y pasar su URI a través de esta variable.
 3.  **Logging**: Utiliza el cliente de logging de Google Cloud, lo que permite que los logs se integren automáticamente con Cloud Logging cuando se despliega en GCP.
 4.  **Puerto**: El servidor se ejecuta en el puerto definido por la variable de entorno `PORT`, que es la forma en que Cloud Run asigna un puerto al contenedor.
 
 ## 6. Contenedorización (`Dockerfile`)
 
 El `Dockerfile` define los pasos para empaquetar la aplicación en una imagen de contenedor portable y reproducible.
 
 ```dockerfile
 # 1. Usar una imagen base oficial de Python
 FROM python:3.12-slim
 
 # 2. Establecer el directorio de trabajo dentro del contenedor
 WORKDIR /app
 
 # 3. Copiar el archivo de dependencias
 COPY requirements.txt .
 
 # 4. Instalar las dependencias
 RUN pip install --no-cache-dir -r requirements.txt
 
 # 5. Copiar todo el código de la aplicación
 COPY . .
 
 # 6. Exponer el puerto que Cloud Run usará para enviar tráfico
 EXPOSE 8080
 
 # 7. Comando para ejecutar la aplicación al iniciar el contenedor
 # Se usa la variable de entorno $PORT que Cloud Run provee dinámicamente.
 CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]
 ```
 
 ## 7. Despliegue en Google Cloud
 
 El despliegue se realiza en dos pasos principales: construir la imagen del contenedor y desplegarla en Cloud Run.
 
 ### Paso 1: Construir y Subir la Imagen a Artifact Registry
 
 Este comando utiliza Cloud Build para construir la imagen Docker a partir del `Dockerfile` en el directorio actual y la etiqueta (`tag`) para subirla al repositorio de Artifact Registry especificado.
 
 ```bash
 gcloud builds submit --tag us-central1-docker.pkg.dev/vertex-466215/agent-sofia-repo/agent-sofia:latest .
 ```
 
 ### Paso 2: Desplegar el Contenedor en Cloud Run
 
 Este comando despliega la imagen previamente subida como un nuevo servicio en Cloud Run.
 
 ```bash
 gcloud run deploy agent-sofia \
   --image=us-central1-docker.pkg.dev/vertex-466215/agent-sofia-repo/agent-sofia:latest \
   --platform=managed \
   --region=us-central1 \
   --allow-unauthenticated \
   --set-env-vars="GOOGLE_CLOUD_PROJECT=vertex-466215,GOOGLE_CLOUD_LOCATION=us-central1,GOOGLE_GENAI_USE_VERTEXAI=True"
 ```
 
 ### Análisis de los Parámetros de Despliegue:
 -   `--image`: Especifica la URL completa de la imagen de contenedor a desplegar.
 -   `--platform=managed`: Indica que se usará la plataforma de Cloud Run totalmente gestionada por Google.
 -   `--region`: La región de GCP donde se desplegará el servicio.
 -   `--allow-unauthenticated`: Permite que el servicio sea invocado públicamente sin autenticación de IAM. **Nota:** Para servicios privados, este flag debe omitirse.
 -   `--set-env-vars`: Establece las variables de entorno para el servicio en ejecución:
     -   `GOOGLE_CLOUD_PROJECT`: ID del proyecto de GCP.
     -   `GOOGLE_CLOUD_LOCATION`: Región por defecto para los servicios de GCP.
     -   `GOOGLE_GENAI_USE_VERTEXAI=True`: Indica al SDK de GenAI que utilice los endpoints y la autenticación de Vertex AI.