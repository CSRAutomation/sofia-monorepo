import os
import sys
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging

# Configurar logging
app = Flask(__name__)

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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=True)