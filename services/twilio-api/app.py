import os
import sys
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.voice_response import VoiceResponse, Gather
import logging
import requests

# Configurar logging
app = Flask(__name__)

# Cargar credenciales desde variables de entorno (inyectadas por Cloud Run)
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
AGENT_API_URL = os.environ.get("AGENT_API_URL") # URL para comunicarse con el agente Sofía
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

required_secrets = {
    "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
    "TWILIO_PHONE_NUMBER": TWILIO_PHONE_NUMBER
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

@app.route('/sms/send', methods=['POST'])
def send_sms():
    # Obtener el cliente a través de la función singleton
    client = get_twilio_client()

    data = request.json
    to_number = data.get('to')
    body = data.get('body')

    if not all([to_number, body]):
        return jsonify({"status": "error", "message": "Se requieren los campos 'to' y 'body'."}), 400

    try:
        message = client.messages.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            body=body)
        app.logger.info(f"SMS enviado con éxito. SID: {message.sid}")
        return jsonify({"status": "success", "sid": message.sid}), 200
    except TwilioRestException as e:
        # Captura errores específicos de la API de Twilio para dar una respuesta más útil.
        app.logger.error(f"Error de la API de Twilio: {e.msg} (Código: {e.code})")
        return jsonify({"status": "error", "message": "Error de la API de Twilio.", "details": e.msg, "code": e.code}), 400
    except Exception as e:
        # Captura cualquier otro error inesperado.
        app.logger.error(f"Error inesperado al enviar SMS: {e}")
        return jsonify({"status": "error", "message": "Ocurrió un error inesperado en el servidor."}), 500

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