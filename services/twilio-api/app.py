import os
import sys
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.twiml.messaging_response import MessagingResponse
import logging
import requests


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


@app.route('/sms/receive', methods=['POST'])
def receive_sms():
    """
    Recibe un SMS de Twilio, lo procesa con el agente y envía una respuesta.
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

    # 1. Construir el payload para el agente (lógica de pruebas-agente-api.py)
    payload = {
        "app_name": AGENT_APP_NAME,
        "user_id": user_id,
        "session_id": session_id,
        "new_message": {
            "role": "user",
            "parts": [{"text": message_body}]
        }
    }

    agent_response_text = "Lo siento, no pude procesar tu solicitud en este momento." # Mensaje de error por defecto

    try:
        # 2. Enviar el mensaje al agente
        agent_response = requests.post(AGENT_API_URL, json=payload, timeout=25)
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
            if full_response: # Asegurarse de que no esté vacío
                agent_response_text = full_response

    except requests.exceptions.RequestException as e:
        app.logger.error(f"Error al conectar con el agente para la sesión {session_id}: {e}")
    except (ValueError, KeyError) as e: # ValueError puede ser por json.JSONDecodeError
        app.logger.error(f"Error al parsear la respuesta del agente para la sesión {session_id}: {e}")

    try:
        # 4. Enviar la respuesta del agente de vuelta al usuario vía SMS
        client = get_twilio_client()
        client.messages.create(to=from_number, from_=TWILIO_PHONE_NUMBER, body=agent_response_text)
        app.logger.info(f"Respuesta enviada a {from_number}: '{agent_response_text}'")
    except TwilioRestException as e:
        app.logger.error(f"Error de Twilio al enviar respuesta a {from_number}: {e.msg}")

    return str(MessagingResponse()), 200

@app.route("/voice", methods=['POST'])
def voice_webhook():
    """Maneja las llamadas de voz entrantes y las respuestas del agente."""
    twiml_response = VoiceResponse()

    # Obtener el texto transcrito de la voz del usuario, si existe.
    user_speech = request.values.get('SpeechResult', None)
    call_sid = request.values.get('CallSid') # Usar CallSid como session_id

    agent_text_response = ""

    # --- Bloque de prueba sin conectar al agente ---
    # Este código responde con textos pre-programados para probar la generación de voz.
    if user_speech:
        app.logger.info(f"Usuario (CallSid: {call_sid}) dijo: '{user_speech}'")
        # Respondemos con un texto que repite lo que dijo el usuario.
        agent_text_response = f"Ha dicho: {user_speech}. Esta es una prueba de la generación de voz. Diga algo más para continuar la prueba."
    else:
        # Este es el primer turno de la llamada, el saludo inicial de prueba.
        agent_text_response = "Hola. Esta es una prueba de la API de voz de Twilio. Por favor, diga algo después del tono."

    # Usamos <Gather> para decir la respuesta del agente y luego escuchar al usuario.
    # El verbo 'say' se anida dentro de 'gather'.
    gather = Gather(input='speech', speechTimeout='auto', language='es-US', action='/voice')

    # Usamos una voz Neural Premium (Polly.Mia-Neural) para un habla mucho más natural.
    # El idioma 'es-MX' suele dar excelentes resultados para el español de América.
    gather.say(agent_text_response, language='es-MX', voice='Polly.Mia-Neural')

    twiml_response.append(gather)

    # Si el usuario no dice nada después del timeout, la llamada se redirige aquí
    # y el ciclo comienza de nuevo, lo que puede hacer que el agente repita la última pregunta.
    twiml_response.redirect('/voice')

    return str(twiml_response), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)