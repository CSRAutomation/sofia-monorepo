# Agente Sofía - Documentación Técnica

Este documento proporciona una descripción técnica detallada del microservicio `agent-sofia`, el cerebro del proyecto agente de inteligencia aritificial para atencion al cliente.

---

## 1. Finalidad y Objetivos del Proyecto

El **Agente Sofía** es un asistente de inteligencia artificial conversacional diseñado para automatizar y mejorar la experiencia de servicio al cliente de **FrancisTaxService**.

### Objetivos Clave:

-   **Atención Autónoma:** Gestionar interacciones con clientes de principio a fin sin intervención humana para tareas comunes.
-   **Gestión de Datos en Salesforce:** Actuar como una interfaz de lenguaje natural para Salesforce, permitiendo:
    -   Buscar contactos existentes.
    -   Verificar la identidad de los clientes de forma segura.
    -   Crear nuevos contactos cuando sea necesario.
    -   Registrar cada interacción como un caso de servicio (`Customer_Service__c`).
-   **Experiencia de Usuario Natural:** Mantener una conversación fluida, amable y profesional, haciendo que el cliente se sienta escuchado y bien atendido.
-   **Inteligencia de Contexto:** Diferenciar entre un cliente que llama por sí mismo y un representante que llama en nombre de un cliente, adaptando el flujo de la conversación.

---

## 2. Arquitectura del Servicio

`agent-sofia` es una aplicación **FastAPI** en donde envolvemos el servicio de IA de**Google Agent Development Kit (ADK)**. Funciona como un microservicio dentro de la arquitectura general y es responsable de toda la lógica conversacional.

### Interacciones con otros Servicios:

-   **Invocado por:** `twilio-api`. Este servicio actúa como puerta de enlace para los canales de comunicación (SMS, Voz, Chat-Web, WhatsApp) y reenvía los mensajes del usuario al agente.
-   **Invoca a:** `salesforce-api`. Cuando el agente necesita interactuar con Salesforce (para buscar un contacto, verificarlo o crear un registro), realiza llamadas HTTP a los endpoints expuestos por el servicio `salesforce-api`.

### Configuración y Variables de Entorno

El comportamiento del servicio se configura a través de variables de entorno, que son inyectadas por Cloud Run durante el despliegue.

-   `GOOGLE_CLOUD_PROJECT`: ID del proyecto de Google Cloud, necesario para la integración con servicios de GCP como Vertex AI.
-   `GOOGLE_CLOUD_LOCATION`: Región de GCP donde operan los servicios.
-   `GOOGLE_GENAI_USE_VERTEXAI`: Indica al ADK que utilice los modelos de Vertex AI para la generación de respuestas.
-   `SALESFORCE_API_URL`: La URL del servicio `salesforce-api` para que el agente pueda realizar las llamadas a su API.
-   `PORT`: El puerto en el que se ejecuta el servidor web (proporcionado por Cloud Run, por defecto `8080`).

---

## 3. Lógica Central: El Prompt del Sistema

El "cerebro" y la personalidad de Sofía están definidos en un único y detallado prompt de sistema ubicado en `sofia_agent/prompts.py`. Este prompt instruye al modelo de lenguaje sobre cómo comportarse, qué herramientas usar y cómo seguir flujos de trabajo específicos.

### Componentes Clave del Prompt:

1.  **Persona:** Define a Sofía como una representante de servicio al cliente amable, profesional y natural. Establece reglas como el uso del pronombre "usted".
2.  **Misión Principal:** Guía al agente en su objetivo: identificar al usuario, verificar su identidad y registrar la interacción.
3.  **Flujo de Trabajo Lógico:** Es la sección más crítica. Define una máquina de estados conversacional basada en condiciones (`{{{State.Some.VALUE}}}`).
    -   **Identificación Inicial (Casos A, B, C, D):** Detalla cómo reaccionar si el usuario da un nombre completo, un nombre parcial, se identifica como representante o no se identifica.
    -   **Verificación de Identidad:** Especifica el proceso de solicitar la fecha de nacimiento (DOB) y, si falla, un número de teléfono como método alternativo.
    -   **Manejo de Cliente No Encontrado:** Define cómo proceder si el contacto no existe en Salesforce, ofreciendo crear una nueva cuenta.
    -   **Creación de Registro de Servicio:** Una vez verificado el cliente, detalla los pasos para recopilar la información necesaria y crear el registro `Customer_Service__c`.
4.  **Guía de Conversación:** Ofrece ejemplos de diálogos para inspirar el tono y estilo del agente, pero enfatiza que **no es un guion estricto**, promoviendo la adaptabilidad.
5.  **Reglas Globales:** Impone reglas críticas de comportamiento, como no revelar que es una IA, justificar la solicitud de datos y narrar siempre las acciones antes de ejecutarlas.

---

## 4. Integración de Herramientas (Tools)

El agente utiliza "herramientas" (tools) para realizar acciones en el mundo real. Estas herramientas son funciones que el modelo de IA decide llamar en función de la conversación. En este proyecto, las herramientas son llamadas a la API de `salesforce-api`.

El prompt define cuándo usar herramientas como:
-   `salesforce_find_contact_by_name`: Para buscar un contacto.
-   `salesforce_verify_contact_by_dob`: Para verificar la identidad.
-   `salesforce_create_contact`: Para crear un nuevo cliente.
-   `salesforce_create_customer_service`: Para registrar la interacción.

La implementación de estas herramientas se encuentra en los archivos de `tools` dentro del directorio del agente, y su lógica consiste principalmente en realizar una petición `requests` al servicio `salesforce-api`.

---

## 5. Desarrollo Local

Para ejecutar el agente en un entorno local:

1.  **Crear un entorno virtual e instalar dependencias:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # En Windows: venv\Scripts\activate
    pip install -r services/agent-sofia/requirements.txt
    ```

2.  **Configurar variables de entorno:**
    Crea un archivo `.env` en el directorio `services/agent-sofia/` con el siguiente contenido. Asegúrate de que el servicio `salesforce-api` se esté ejecutando localmente y su URL sea correcta.
    ```env
    # services/agent-sofia/.env

    GOOGLE_CLOUD_PROJECT="tu-gcp-project-id"
    GOOGLE_CLOUD_LOCATION="us-central1"
    GOOGLE_GENAI_USE_VERTEXAI="True"
    SALESFORCE_API_URL="http://127.0.0.1:8081" # URL local del servicio salesforce-api
    ```

3.  **Ejecutar el servidor:**
    Desde la raíz del monorepo, ejecuta:
    ```bash
    uvicorn services.agent-sofia.main:app --reload --port 8080
    ```
    El servidor estará disponible en `http://127.0.0.1:8080`.

---

## 6. Despliegue

El servicio `agent-sofia` está diseñado para ser desplegado en **Cloud Run**.

### Despliegue en Entorno de Desarrollo/Pruebas

Para desplegar manualmente los cambios de tu rama actual al entorno de desarrollo, utiliza el script `cloudbuild-dev.yaml`. Este script se encarga de construir la imagen, publicarla en Artifact Registry y desplegarla en Cloud Run con la configuración de desarrollo (ej. `agent-sofia-dev-service`).

Ejecuta el siguiente comando desde la raíz del monorepo:
```bash
gcloud builds submit --config cloudbuild-dev.yaml --substitutions=_SERVICE_NAME=agent-sofia
```

**Nota Importante:** El agente se despliega como un servicio público (`--allow-unauthenticated`) porque necesita ser invocado por el servicio `twilio-api`, que a su vez es invocado por webhooks externos de Twilio.

### Despliegue en Producción

El despliegue a producción es automático. Cuando los cambios se fusionan (merge) a la rama `main`, un disparador de Cloud Build se activa, utilizando el archivo `cloudbuild.yaml` para desplegar la versión de producción (`agent-sofia-service`).