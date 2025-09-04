# Plataforma de IA Sofia - Agente de Servicio al Cliente Omnicanal

Este repositorio alberga el código fuente de **Sofia**, un agente de inteligencia artificial diseñado para revolucionar la atención al cliente a través de una experiencia omnicanal y fluida.

---

## 1. Misión del Proyecto

El objetivo principal de Sofia es proporcionar un servicio al cliente excepcional, automatizado e inteligente, capaz de interactuar con los usuarios a través de múltiples canales de comunicación.

### Capacidades del Agente

Sofia está siendo desarrollada para:
- **Responder consultas** de los usuarios de forma autónoma y precisa.
- **Crear y gestionar contactos** directamente en Salesforce.
- **Abrir nuevos casos de servicio** y dar seguimiento a los existentes.
- **Agendar citas** de manera eficiente.
- **Escalar conversaciones** de forma inteligente a personal capacitado cuando una solicitud exceda sus capacidades.

### Enfoque Omnicanal

La plataforma está diseñada para integrarse con los siguientes canales, ofreciendo una experiencia de usuario consistente:
- Llamadas de Voz
- SMS
- WhatsApp
- Chat Web

---

## 2. Arquitectura y Estructura del Monorepo

La plataforma se construye sobre una arquitectura de microservicios gestionada dentro de este **monorepo**. Este enfoque nos permite centralizar el código, facilitar la reutilización de lógica y agilizar el desarrollo.
- **Código Compartido:** La lógica común (ej. modelos de datos, clientes de autenticación) se escribe una vez en el directorio `libs/` y se reutiliza en todos los servicios.
- **Cambios Atómicos:** Un solo commit o Pull Request puede aplicar un cambio a través de múltiples servicios y librerías, garantizando la consistencia.
- **Tooling Unificado:** Se utiliza una sola configuración para herramientas de calidad de código, formateo y análisis estático.
- **Gestión de Dependencias Simplificada:** Se facilita el mantenimiento de versiones consistentes de las librerías en todo el proyecto.

---

```
sofia-monorepo/
├── services/
│   ├── salesforce-api/      # API para interactuar con Salesforce
│   ├── twilio-api/          # API para interactuar con Twilio
│   └── main-agent/          # Lógica principal del agente de IA
│
├── libs/                    # Librerías de Python compartidas
│   └── ...
│
└── cloudbuild.yaml          # Pipeline de CI/CD principal y genérico
```

- **`services/`**: Contiene el código de cada microservicio desplegable. Cada subdirectorio es una aplicación autocontenida con su propio `Dockerfile` y `requirements.txt`.
- **`libs/`**: Contiene librerías de Python diseñadas para ser compartidas entre los diferentes servicios.
- **`cloudbuild.yaml`**: Es el archivo de configuración principal para Cloud Build. Es genérico y utiliza variables para construir y desplegar cualquier servicio del directorio `services/`.

---

## 3. Flujo de Trabajo de Desarrollo

El flujo de trabajo está diseñado para ser simple y eficiente, aprovechando las capacidades de Git y Cloud Build.

1.  **Crear una Rama:** Todo nuevo desarrollo o corrección de errores debe hacerse en una rama de feature a partir de `main`.
    ```bash
    git checkout main
    git pull
    git checkout -b feature/nombre-de-tu-feature
    ```

2.  **Realizar Cambios:** Modifica el código en los servicios o librerías que necesites.

3.  **Integrar Cambios:** Una vez finalizado tu trabajo, abre un Pull Request (PR) hacia la rama `main`.

4.  **Despliegue Automático (CI/CD):** Al hacer merge del PR a `main`, los disparadores de Cloud Build se activarán automáticamente:
    - **Detección de Cambios:** Cloud Build detectará qué directorios de servicio (`services/*`) han sido modificados.
    - **Build Selectivo:** Se construirá y desplegará **únicamente** el contenedor del servicio que cambió. Si un cambio afecta a múltiples servicios (por ejemplo, un cambio en `libs/`), se dispararán los builds para todos los servicios dependientes.

---

## 4. Despliegue de Servicios

### Despliegue Automático (Recomendado)

El despliegue se gestiona a través de **Disparadores de Cloud Build**. Hay un disparador configurado para cada servicio, que vigila los cambios en su directorio específico dentro de la rama `main`.

### Despliegue Manual

Si necesitas desplegar un servicio manualmente, puedes usar el siguiente comando desde la raíz del repositorio, reemplazando `<nombre-del-servicio>` por el nombre del directorio del servicio (ej. `salesforce-api`).

```bash
gcloud builds submit --config cloudbuild.yaml --substitutions=_SERVICE_NAME=<nombre-del-servicio>
```

---

¡Listo! Con esta estructura, estamos preparados para construir de forma ordenada y escalable. El siguiente paso es configurar los disparadores en Cloud Build. ¡Vamos a ello!