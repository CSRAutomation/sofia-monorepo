import os
import sys
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.twiml.messaging_response import MessagingResponse
import logging

# Configurar logging
# Se elimina logging.basicConfig() para que Gunicorn/Cloud Run lo manejen.
app = Flask(__name__)

# Cuando se ejecuta en producción con Gunicorn (como en Cloud Run),
# es mejor usar el logger de Gunicorn para que los logs sean consistentes.
if __name__ != '__main__':
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)

# Cargar credenciales desde variables de entorno (inyectadas por Cloud Run)
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

required_secrets = {
    "TWILIO_ACCOUNT_SID": ACCOUNT_SID,
    "TWILIO_AUTH_TOKEN": AUTH_TOKEN,
    "TWILIO_PHONE_NUMBER": TWILIO_PHONE_NUMBER
}
missing_secrets = [key for key, value in required_secrets.items() if not value]

if missing_secrets:
    error_message = f"Error crítico: Faltan las siguientes variables de entorno de Twilio: {', '.join(missing_secrets)}"
    app.logger.critical(error_message)
    sys.exit(1)

# --- Inicialización Singleton del Cliente de Twilio ---
twilio_client = None

def get_twilio_client():
    """
    Establece y gestiona una conexión singleton con Twilio.
    """
    global twilio_client
    if twilio_client is None:
        app.logger.info("Inicializando cliente de Twilio...")
        # La inicialización del cliente puede lanzar una excepción si las credenciales son inválidas.
        twilio_client = Client(ACCOUNT_SID, AUTH_TOKEN)
        app.logger.info("¡Cliente de Twilio inicializado con éxito!")
    return twilio_client

@app.route('/health', methods=['GET'])
def health_check():
    """Endpoint de verificación de estado para Cloud Run."""
    return jsonify({"status": "ok"}), 200

# FIX: Se corrige la ruta para que coincida con la que se está llamando ('/send/sms')
# y así resolver el error 404 Not Found.
@app.route('/send/sms', methods=['POST'])
def send_sms():
    # Obtener el cliente a través de la función singleton
    client = get_twilio_client()

    data = request.json
    to_number = data.get('to')

    if not to_number:
        return jsonify({"status": "error", "message": "El campo 'to' es requerido."}), 400

    # Se define un mensaje predeterminado para la prueba de comunicación.
    # El cuerpo del mensaje ('body') ya no se necesita en la petición JSON.
    test_message_body = "Este es un mensaje de prueba desde la API de Sofia para verificar la comunicación."

    try:
        message = client.messages.create(
            to=to_number,
            from_=TWILIO_PHONE_NUMBER,
            body=test_message_body)
        app.logger.info(f"SMS de prueba enviado con éxito. SID: {message.sid}")
        return jsonify({"status": "success", "sid": message.sid}), 200
    except TwilioRestException as e:
        # Captura errores específicos de la API de Twilio para dar una respuesta más útil.
        app.logger.error(f"Error de la API de Twilio: {e.msg} (Código: {e.code})")
        return jsonify({"status": "error", "message": "Error de la API de Twilio.", "details": e.msg, "code": e.code}), 400
    except Exception as e:
        # Captura cualquier otro error inesperado.
        app.logger.error(f"Error inesperado al enviar SMS: {e}")
        return jsonify({"status": "error", "message": "Ocurrió un error inesperado en el servidor."}), 500

@app.route('/sms/receive', methods=['POST'])
def receive_sms():
    """
    Endpoint para recibir mensajes SMS entrantes de Twilio (Webhook).
    Al recibir un mensaje, envía un mensaje de prueba predeterminado
    de vuelta al remitente usando la API REST.
    """
    # Extraer el cuerpo del mensaje y el número del remitente
    incoming_body = request.values.get('Body', None)
    from_number = request.values.get('From', None)

    app.logger.info(f"Mensaje recibido de {from_number}: '{incoming_body}'")

    if not from_number:
        app.logger.error("No se pudo obtener el 'From' number del webhook de Twilio.")
        # Devolvemos una respuesta vacía para que Twilio no intente reenviar el webhook.
        return str(MessagingResponse()), 200

    # Obtener el cliente de Twilio y definir el mensaje de prueba
    client = get_twilio_client()
    test_message_body = "Este es un mensaje de prueba desde la API de Sofia para verificar la comunicación."

    try:
        # Enviar el mensaje de prueba de vuelta al remitente
        message = client.messages.create(
            to=from_number,
            from_=TWILIO_PHONE_NUMBER,
            body=test_message_body
        )
        app.logger.info(f"SMS de prueba de respuesta enviado a {from_number}. SID: {message.sid}")
    except TwilioRestException as e:
        app.logger.error(f"Error de la API de Twilio al responder: {e.msg} (Código: {e.code})")
    except Exception as e:
        app.logger.error(f"Error inesperado al enviar SMS de respuesta: {e}")

    # Twilio espera una respuesta TwiML. Devolvemos una vacía para indicar que
    # hemos procesado la solicitud y no queremos que Twilio envíe otra respuesta.
    response = MessagingResponse()
    return str(response), 200, {'Content-Type': 'application/xml'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # El modo debug no debe usarse en producción. Es mejor controlarlo con una variable de entorno.
    app.run(host="0.0.0.0", port=port, debug=os.environ.get("FLASK_DEBUG", "False").lower() in ("true", "1"))