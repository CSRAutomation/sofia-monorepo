import os
import sys
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
import logging
import requests
import time


# Configurar logging
app = Flask(__name__)

# Cargar credenciales desde variables de entorno (inyectadas por Cloud Run)
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
AGENT_API_URL = os.environ.get("AGENT_API_URL") # URL para comunicarse con el agente Sofía
AGENT_APP_NAME = os.environ.get("AGENT_APP_NAME", "sofia_agent") # Nombre de la app del agente
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

required_secrets = {
    "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
    "TWILIO_PHONE_NUMBER": TWILIO_PHONE_NUMBER,
    "AGENT_API_URL": AGENT_API_URL
}
missing_secrets = [key for key, value in required_secrets.items() if not value]

if missing_secrets:
    error_message = f"Error crítico: Faltan las siguientes variables de entorno de Twilio: {', '.join(missing_secrets)}"
    logging.critical(error_message)
    sys.exit(1)

# --- Inicialización Singleton del Cliente de Twilio ---
twilio_client = None

def get_twilio_client():
    """
    Establece y gestiona una conexión singleton con Twilio.
    """
    global twilio_client
    if twilio_client is None:
        app.logger.info("Estableciendo nueva conexión con Twilio...")
        try:
            twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
            app.logger.info("¡Conexión con Twilio exitosa!")
        except Exception as e:
            app.logger.error(f"Error inesperado durante la conexión a Twilio: {e}")
            raise
    return twilio_client

def ensure_agent_session_exists(user_id: str, session_id: str):
    """
    Asegura que una sesión exista para un usuario en el agente.

    Este método es eficiente: intenta crear la sesión directamente con POST.
    Si la sesión ya existe, la API devuelve un código 409 (Conflict),
    que se maneja como un caso de éxito, evitando una llamada de red adicional
    (como GET o HEAD) solo para verificar la existencia.

    Lanza una excepción `requests.exceptions.RequestException` si la API
    devuelve un error inesperado.
    """
    create_session_url = f"{AGENT_API_URL}/apps/{AGENT_APP_NAME}/users/{user_id}/sessions/{session_id}"
    app.logger.info(f"Asegurando que la sesión '{session_id}' exista para el usuario '{user_id}'.")
    
    response = requests.post(create_session_url, timeout=15)

    # Si la sesión ya existe, la API puede devolver 409 Conflict. Esto se considera un éxito.
    if response.status_code == 400:
        app.logger.info(f"La sesión '{session_id}' ya existía.")
        return

    # Para cualquier otro código de error (4xx, 5xx), se lanza una excepción.
    response.raise_for_status()
    app.logger.info(f"Sesión '{session_id}' creada exitosamente.")

@app.route('/sms/receive', methods=['POST'])
def receive_sms():
    """
    Recibe un SMS de Twilio, lo procesa con el agente y envía una o más respuestas.
    """
    # Extraer datos del webhook de Twilio
    from_number = request.values.get('From', None)
    message_body = request.values.get('Body', None)
    app.logger.info(f"SMS recibido de {from_number}: '{message_body}'")
 
    if not from_number or not message_body:
        app.logger.warning("Webhook de Twilio recibido sin 'From' o 'Body'.")
        return str(MessagingResponse()), 200
 
    # Usar el número de teléfono como ID de sesión y de usuario para mantener el contexto
    session_id = from_number
    user_id = from_number
 
    try:
        # --- Creación/Verificación de Sesión ---
        ensure_agent_session_exists(user_id, session_id)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error crítico al crear/verificar la sesión '{session_id}': {e}")
        # Informar al usuario que hay un problema de sistema
        error_message = "Lo siento, estamos teniendo problemas para iniciar la conversación. Por favor, intenta de nuevo en unos minutos."
        try:
            client = get_twilio_client()
            client.messages.create(to=from_number, from_=TWILIO_PHONE_NUMBER, body=error_message)
        except TwilioRestException as twilio_e:
            app.logger.error(f"Fallo al enviar SMS de error de sesión a {from_number}: {twilio_e.msg}")

        # Devolvemos 200 a Twilio para que no reintente el webhook.
        return str(MessagingResponse()), 200

    # 1. Construir el payload para el agente
    payload = {
        "app_name": AGENT_APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": message_body}]
        }
    }
 
    responses_to_send = []
 
    try:
        # 2. Enviar el mensaje al agente y procesar la respuesta
        agent_response = requests.post(f"{AGENT_API_URL}/run", json=payload, timeout=25)
        agent_response.raise_for_status()
        response_data = agent_response.json()

        # 3. Extraer la respuesta de texto del agente
        agent_messages = []
        if isinstance(response_data, list):
            for turn in response_data:
                if 'content' in turn and 'parts' in turn['content']:
                    for part in turn['content']['parts']:
                        if 'text' in part and part.get('text'):
                            agent_messages.append(part['text'])
        
        if agent_messages:
            full_response = "".join(agent_messages).strip()
            # Aplicamos la lógica del script de pruebas: separamos por saltos de línea
            individual_responses = [msg.strip() for msg in full_response.split('\n') if msg.strip()]
            if individual_responses:
                responses_to_send.extend(individual_responses)
 
    except (requests.exceptions.RequestException, ValueError, KeyError) as e:
        app.logger.error(f"Error procesando la respuesta del agente para {session_id}: {e}")
        # Dejamos la lista responses_to_send vacía para que se envíe el mensaje de error por defecto.
        pass
 
    # 4. Si no se pudo obtener una respuesta del agente, usar un mensaje por defecto.
    if not responses_to_send:
        responses_to_send.append("Lo siento, no pude procesar tu solicitud en este momento.")
 
    # 5. Enviar todas las respuestas preparadas como mensajes SMS separados.
    try:
        client = get_twilio_client()
        for i, text_body in enumerate(responses_to_send):
            client.messages.create(to=from_number, from_=TWILIO_PHONE_NUMBER, body=text_body)
            app.logger.info(f"Respuesta ({i+1}/{len(responses_to_send)}) enviada a {from_number}: '{text_body}'")
            # Simulamos una pausa entre mensajes para una experiencia más natural, como en el script de prueba.
            if len(responses_to_send) > 1 and i < len(responses_to_send) - 1:
                time.sleep(1.5)
    except TwilioRestException as e:
        app.logger.error(f"Error de Twilio al enviar respuesta a {from_number}: {e.msg}")
 
    return str(MessagingResponse()), 200

@app.route("/voice", methods=['POST'])
def voice_webhook():
    """Maneja las llamadas de voz entrantes y las respuestas del agente."""
    twiml_response = VoiceResponse()

    # Extraer datos del webhook de Twilio. Usar "" como default para el primer turno.
    user_speech = request.values.get('SpeechResult', "")
    call_sid = request.values.get('CallSid')
    from_number = request.values.get('From')

    # Validar que tengamos los identificadores necesarios para la sesión.
    if not call_sid or not from_number:
        app.logger.error("Webhook de voz recibido sin CallSid o From.")
        twiml_response.say(
            "Lo siento, ha ocurrido un error de sistema. Por favor, intente llamar de nuevo más tarde.",
            language='es-MX', voice='Polly.Mia-Neural'
        )
        twiml_response.hangup()
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}

    # Usar CallSid como ID de sesión y el número del llamante como ID de usuario.
    session_id = call_sid
    user_id = from_number
    app.logger.info(f"Llamada (SID: {session_id}) de {user_id}. Transcripción: '{user_speech}'")

    # --- Creación/Verificación de Sesión con el Agente ---
    try:
        ensure_agent_session_exists(user_id, session_id)
    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error crítico al crear/verificar la sesión de voz '{session_id}': {e}")
        twiml_response.say(
            "Lo siento, estamos teniendo problemas para iniciar la conversación. Por favor, intente llamar de nuevo en unos minutos.",
            language='es-MX', voice='Polly.Mia-Neural'
        )
        twiml_response.hangup()
        return str(twiml_response), 200, {'Content-Type': 'text/xml'}

    # --- Interacción con el Agente ---
    # 1. Construir el payload para el agente. Un user_speech vacío iniciará la conversación.
    payload = {
        "app_name": AGENT_APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": user_speech}]
        }
    }

    agent_text_response = ""
    should_hangup = False # Flag para determinar si la llamada debe terminarse.

    try:
        # 2. Enviar el mensaje al agente y procesar la respuesta.
        agent_api_response = requests.post(f"{AGENT_API_URL}/run", json=payload, timeout=25)
        agent_api_response.raise_for_status() # Lanza HTTPError para 4xx/5xx
        response_data = agent_api_response.json()

        # 3. Extraer la respuesta de texto del agente.
        agent_messages = []
        if isinstance(response_data, list):
            for turn in response_data:
                if 'content' in turn and 'parts' in turn['content']:
                    for part in turn['content']['parts']:
                        if 'text' in part and part.get('text'):
                            agent_messages.append(part['text'])
        
        if agent_messages:
            # Para voz, unimos todas las partes en una sola respuesta.
            agent_text_response = "".join(agent_messages).strip()
        else:
            # El agente respondió, pero sin texto.
            app.logger.warning(f"El agente respondió sin contenido de texto para la llamada {session_id}.")
            agent_text_response = "No he entendido lo que ha dicho. ¿Podría repetirlo, por favor?"

    except requests.exceptions.ConnectionError as e:
        app.logger.error(f"Error de conexión con el agente para la llamada {session_id}: {e}")
        agent_text_response = "No es posible conectarnos con el agente en este momento. El servicio parece no estar en ejecución. Por favor, intente de nuevo en unos minutos."
        should_hangup = True

    except requests.exceptions.Timeout as e:
        app.logger.error(f"Timeout al conectar con el agente para la llamada {session_id}: {e}")
        agent_text_response = "Nuestro sistema está tardando más de lo normal en responder. ¿Podría repetir su consulta, por favor?"

    except requests.exceptions.HTTPError as e:
        app.logger.error(f"Error HTTP del agente para la llamada {session_id}: {e}")
        agent_text_response = "Hemos encontrado un error interno en nuestro sistema. Nuestro equipo técnico ya ha sido notificado. Por favor, intente llamar de nuevo más tarde."
        should_hangup = True

    except (ValueError, KeyError) as e:
        # Error al decodificar JSON o al acceder a una clave esperada.
        app.logger.error(f"Error de formato en la respuesta del agente para la llamada {session_id}: {e}")
        agent_text_response = "Hemos recibido una respuesta con un formato inesperado. ¿Podría intentar su consulta de nuevo?"

    except requests.exceptions.RequestException as e:
        # Captura cualquier otra excepción de la librería requests.
        app.logger.error(f"Error de red inesperado con el agente para la llamada {session_id}: {e}")
        agent_text_response = "Se ha producido un error de comunicación de red. Por favor, intente de nuevo."
        should_hangup = True

    # Fallback final si, por alguna razón, la respuesta sigue vacía.
    if not agent_text_response:
        agent_text_response = "Lo siento, no pude procesar su solicitud en este momento. ¿Podría repetirlo, por favor?"

    app.logger.info(f"Respuesta del agente para la llamada {session_id}: '{agent_text_response}'")

    # --- Generación de TwiML para la Respuesta ---
    # Si debemos colgar, solo decimos el mensaje y colgamos.
    if should_hangup:
        twiml_response.say(agent_text_response, language='es-MX', voice='Polly.Mia-Neural')
        twiml_response.hangup()
    else:
        # Si no, continuamos la conversación con Gather.
        gather = Gather(input='speech', speechTimeout='auto', language='es-US', action='/voice')
        gather.say(agent_text_response, language='es-MX', voice='Polly.Mia-Neural')
        twiml_response.append(gather)

        twiml_response.redirect('/voice')

    return str(twiml_response), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)