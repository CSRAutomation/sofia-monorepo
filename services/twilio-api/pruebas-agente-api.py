import requests
import json
import time
import random
import uuid
import sys

# --- CONFIGURACIÓN ---
BASE_URL = "https://agent-sofia-service-604477693185.us-central1.run.app"
APP_NAME = "sofia_agent"
USER_ID = "Test Api"
CHAT_API_URL = f"{BASE_URL}/run"

def test_agent_chat(session_id, message=""):
    """
    Envía un mensaje al endpoint del agente y muestra solo la respuesta de texto.
    """
    # Estructura del payload que espera el nuevo agente
    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id, # ID de sesión para mantener el contexto
        "new_message": {
            "role": "user",
            "parts": [
                {"text": message}
            ]
        }
    }

    try:
        # Hacemos la petición POST al agente con un timeout de 15 segundos
        response = requests.post(CHAT_API_URL, json=payload, timeout=15)
        response.raise_for_status()  # Lanza una excepción para respuestas de error (4xx o 5xx)

        response_data = response.json()
        
        # Extraemos solo las partes de texto de la respuesta, ignorando las llamadas a funciones.
        agent_messages = []
        if isinstance(response_data, list):
            for turn in response_data:
                if 'content' in turn and 'parts' in turn['content']:
                    for part in turn['content']['parts']:
                        # Verificamos que el texto no esté vacío, pero lo guardamos completo para respetar los '\n'
                        if 'text' in part and part.get('text'):
                            agent_messages.append(part['text'])
        
        if agent_messages:
            # Simulamos que el agente está "escribiendo" para una experiencia más natural.
            print("Sofía está escribiendo...", end="\r", flush=True)
            time.sleep(random.uniform(0.8, 2.0)) # Espera variable para más realismo

            # Unimos todos los fragmentos y los separamos por saltos de línea para tratarlos como mensajes individuales.
            full_response = "".join(agent_messages)
            individual_responses = [msg.strip() for msg in full_response.split('\n') if msg.strip()]

            # Borramos la línea "escribiendo..." y mostramos la respuesta final.
            print(" " * 30, end="\r")
            for line in individual_responses:
                print(f"Sofía: {line}", flush=True)

    except requests.exceptions.RequestException as e:
        print(f"Error al conectar con el agente: {e}")
    except (json.JSONDecodeError, IndexError, KeyError):
        print("Error: La respuesta del agente no tiene el formato esperado.")
        print(f"Respuesta recibida: {response.text}")

def delete_session(session_id):
    """
    Envía una petición DELETE para eliminar la sesión del agente.
    """
    delete_session_url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"
    try:
        print(f"\nEliminando sesión: {session_id}...")
        response = requests.delete(delete_session_url, timeout=10)
        response.raise_for_status()
        print("¡Sesión eliminada exitosamente!")
    except requests.exceptions.RequestException as e:
        print(f"Advertencia: No se pudo eliminar la sesión. {e}")

if __name__ == "__main__":
    # 1. Generar un ID de sesión dinámico para la nueva conversación.
    session_id = str(uuid.uuid4())

    # 2. Construir la URL para crear la sesión en el servidor del agente.
    create_session_url = f"{BASE_URL}/apps/{APP_NAME}/users/{USER_ID}/sessions/{session_id}"

    # 3. Realizar la llamada POST para crear la sesión.
    try:
        print(f"Creando nueva sesión con ID: {session_id}...")
        response = requests.post(create_session_url, timeout=10)
        response.raise_for_status()
        print("¡Sesión creada exitosamente!")
    except requests.exceptions.RequestException as e:
        print(f"\nError crítico: No se pudo crear la sesión. {e}")
        sys.exit(1)

    try:
        print(f"\nIniciando chat interactivo con Session ID: {session_id}")
        print("Escribe tu mensaje y presiona Enter. Escribe 'salir' para terminar.")

        while True:
            user_message = input("\nTú: ")
            if user_message.lower() in ['salir', 'exit']:
                break
            test_agent_chat(session_id=session_id, message=user_message)
    except KeyboardInterrupt:
        # El bloque finally se encargará de la limpieza.
        pass
    finally:
        print("\nTerminando chat.")
        delete_session(session_id)
