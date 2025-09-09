import httpx
import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict, List, Optional

from google.adk.tools import BaseTool, FunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset
from google.adk.agents.readonly_context import ReadonlyContext
import google.auth
import google.oauth2.id_token

from .states import State

root_dir = Path(__file__).parent.parent.parent
dotenv_path = root_dir / ".env"
load_dotenv(dotenv_path=dotenv_path)


BASE_URL_SALESFORCE_API = os.environ.get("SALESFORCE_API_URL") # Carga desde variable de entorno

logger = logging.getLogger(__name__)

def _get_auth_token(audience: str) -> str:
    """
    Obtiene un token de ID de Google para autenticar peticiones a otros servicios de Cloud Run.
    El 'audience' es la URL del servicio que se va a invocar.
    """
    if not audience:
        raise ValueError("La URL del servicio (audience) no puede estar vacía para obtener un token.")
    try:
        auth_req = google.auth.transport.requests.Request()
        token = google.oauth2.id_token.fetch_id_token(auth_req, audience)
        return token
    except Exception as e:
        logger.error(f"No se pudo obtener el token de autenticación para la audiencia {audience}: {e}")
        raise

def find_contact_by_name(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Busca un contacto en la API de Salesforce por su nombre completo.
    Si lo encuentra, guarda el ID del contacto en el estado.
    Esta herramienta debe usarse una vez que se conozca el nombre completo del cliente para verificar si ya existe.
    """
    tool_context.state[State.Case.CLIENT_SEARCH_ATTEMPTED] = True

    if not full_name:
        message = "Se requiere el nombre completo para buscar un contacto."
        logger.warning(message)
        tool_context.state[State.Case.CLIENT_FOUND] = False
        return {"status": "error", "message": message}

    logger.info(f"Intentando encontrar contacto con el nombre: {full_name}")
    try:
        auth_token = _get_auth_token(BASE_URL_SALESFORCE_API)
        headers = {"Authorization": f"Bearer {auth_token}"}

        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL_SALESFORCE_API}/contact/find",
                json={"full_name": full_name},
                headers=headers,
                timeout=10.0
            )
            # Un 404 es un resultado de negocio válido (no encontrado), no un error del sistema.
            # Lo manejamos explícitamente para evitar que se lance una excepción.
            if response.status_code == 404:
                logger.info(f"Contacto no encontrado para: {full_name} (API devolvió 404).")
                tool_context.state[State.Case.CLIENT_FOUND] = False
                return {"status": "success", "found": False, "message": f"Contacto con nombre '{full_name}' no encontrado."}

            response.raise_for_status()  # Lanza una excepción para otros errores (e.g., 5xx)
            data = response.json()

            if data.get("status") == "found":
                contact = data.get("contact", {})
                contact_id = contact.get("Id")
                account_id = contact.get("AccountId")
                logger.info(f"Contacto encontrado con ID: {contact_id} y AccountId: {account_id}")
                tool_context.state[State.Case.CLIENT_FOUND] = True
                # Se guarda el AccountId en el estado para uso posterior.
                tool_context.state[State.Account.ID] = account_id
                return {"status": "success", "found": True, "contact_id": contact_id, "account_id": account_id}

            elif data.get("status") == "not_found":
                logger.info(f"Contacto no encontrado para: {full_name}")
                tool_context.state[State.Case.CLIENT_FOUND] = False
                return {"status": "success", "found": False, "message": data.get("message")}

            else:  # Maneja otros estados de la API como 'error'
                logger.error(f"La API devolvió un estado de error: {data.get('status')} - {data.get('message')}")
                tool_context.state[State.Case.CLIENT_FOUND] = False
                return {"status": "error", "message": data.get("message", "Error de API desconocido")}

    except httpx.RequestError as e:
        message = f"Error de conexión al buscar contacto: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_FOUND] = False
        return {"status": "error", "message": "No se pudo conectar al servicio de la API."}
    except Exception as e:
        message = f"Ocurrió un error inesperado: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_FOUND] = False
        return {"status": "error", "message": message}

def create_contact(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Crea un nuevo contacto en la API de Salesforce.
    Esta herramienta debe usarse cuando se confirma que un usuario es un nuevo cliente.
    """
    if not full_name:
        message = "Se requiere el nombre completo para crear un contacto."
        logger.warning(message)
        return {"status": "error", "message": message}

    payload = {"full_name": full_name}

    logger.info(f"Intentando crear contacto con payload: {payload}")
    try:
        auth_token = _get_auth_token(BASE_URL_SALESFORCE_API)
        headers = {"Authorization": f"Bearer {auth_token}"}

        with httpx.Client() as client:
            # La creación puede tardar por el Flow de Salesforce, se usa un timeout más largo.
            response = client.post(
                f"{BASE_URL_SALESFORCE_API}/contact/create",
                json=payload,
                headers=headers,
                timeout=20.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "created":
                contact = data.get("contact", {})
                contact_id = contact.get("Id")
                account_id = contact.get("AccountId") # Get the AccountId from the response
                logger.info(f"Contacto creado exitosamente con ID: {contact_id} y asociado a AccountId: {account_id}")
                # Guardar el AccountId, no el ContactId, en el estado de la cuenta.
                if account_id:
                    tool_context.state[State.Account.ID] = account_id
                    # Un cliente recién creado se considera "verificado" para poder continuar con el flujo.
                    tool_context.state[State.Case.CLIENT_VERIFIED] = True
                return {"status": "success", "created": True, "contact_id": contact_id, "account_id": account_id, "contact_data": contact}
            else:
                error_message = data.get("message", "Error desconocido de la API al crear contacto.")
                logger.error(f"La API devolvió un error lógico al crear contacto: {error_message}")
                return {"status": "error", "message": error_message, "details": data.get("details")}

    except httpx.RequestError as e:
        message = f"Error de conexión al crear contacto: {e}"
        logger.error(message)
        return {"status": "error", "message": "No se pudo conectar al servicio de la API."}
    except Exception as e:
        message = f"Ocurrió un error inesperado al crear contacto: {e}"
        logger.error(message)
        return {"status": "error", "message": message}

def verify_contact_by_dob(full_name: str, dob: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Verifica un contacto en la API de Salesforce por su nombre completo y fecha de nacimiento (DOB).
    Si la verificación es exitosa, actualiza el estado para reflejarlo.
    """
    tool_context.state[State.Case.CLIENT_VERIFICATION_ATTEMPTED] = True

    if not all([full_name, dob]):
        message = "Se requieren el nombre completo y la fecha de nacimiento para la verificación."
        logger.warning(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": message}

    # Incrementar el contador de intentos de verificación
    attempts = tool_context.state.get(State.Case.CLIENT_VERIFICATION_ATTEMPTS, 0)
    tool_context.state[State.Case.CLIENT_VERIFICATION_ATTEMPTS] = attempts + 1
    logger.info(
        f"Intentando verificar contacto: {full_name} con DOB: {dob}. Intento #{attempts + 1}"
    )

    try:
        auth_token = _get_auth_token(BASE_URL_SALESFORCE_API)
        headers = {"Authorization": f"Bearer {auth_token}"}

        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL_SALESFORCE_API}/contact/verify/dob",
                json={"full_name": full_name, "dob": dob},
                headers=headers,
                timeout=10.0
            )
            # Un 404 es un resultado de negocio válido (no verificado), no un error del sistema.
            if response.status_code == 404:
                logger.info(f"Verificación fallida para: {full_name} (API devolvió 404).")
                tool_context.state[State.Case.CLIENT_VERIFIED] = False
                return {"status": "success", "verified": False, "message": "No se encontró un contacto que coincida con los datos proporcionados."}

            response.raise_for_status()  # Lanza una excepción para otros errores (e.g., 5xx)

            data = response.json()

            if data.get("status") == "verified":
                contact = data.get("contact", {})
                logger.info(f"Verificación exitosa para el contacto con ID: {contact.get('Id')}")
                tool_context.state[State.Case.CLIENT_VERIFIED] = True
                return {"status": "success", "verified": True, "contact_id": contact.get("Id")}
            else: # Cubre 'not_verified' y otros posibles estados de la API
                logger.info(f"Verificación fallida para: {full_name}")
                tool_context.state[State.Case.CLIENT_VERIFIED] = False
                return {"status": "success", "verified": False, "message": data.get("message")}

    except httpx.RequestError as e:
        message = f"Error de conexión durante la verificación: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": "No se pudo conectar al servicio de la API."}
    except Exception as e:
        message = f"Ocurrió un error inesperado durante la verificación: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": message}

def verify_contact_by_dob_phone(full_name: str, dob: str, phone: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Verifica un contacto en la API de Salesforce por nombre, DOB y teléfono.
    Si la verificación es exitosa, actualiza el estado para reflejarlo.
    """
    if not all([full_name, dob, phone]):
        message = "Se requieren el nombre completo, la fecha de nacimiento y el teléfono para la verificación."
        logger.warning(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": message}

    # Incrementar el contador de intentos de verificación
    attempts = tool_context.state.get(State.Case.CLIENT_VERIFICATION_ATTEMPTS, 0)
    tool_context.state[State.Case.CLIENT_VERIFICATION_ATTEMPTS] = attempts + 1
    logger.info(
        f"Intentando verificar contacto: {full_name} con DOB: {dob} y Teléfono: {phone}. Intento #{attempts + 1}"
    )

    try:
        auth_token = _get_auth_token(BASE_URL_SALESFORCE_API)
        headers = {"Authorization": f"Bearer {auth_token}"}

        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL_SALESFORCE_API}/contact/verify/dob-phone",
                json={"full_name": full_name, "dob": dob, "phone": phone},
                headers=headers,
                timeout=10.0
            )
            if response.status_code == 404:
                data = response.json()
                logger.info(f"Verificación por teléfono fallida para: {full_name} (API devolvió 404).")
                tool_context.state[State.Case.CLIENT_VERIFIED] = False
                return {"status": "success", "verified": False, "message": data.get("message")}

            response.raise_for_status()
            data = response.json()

            if data.get("status") == "verified":
                contact = data.get("contact", {})
                logger.info(f"Verificación por teléfono exitosa para el contacto con ID: {contact.get('Id')}")
                tool_context.state[State.Case.CLIENT_VERIFIED] = True
                return {"status": "success", "verified": True, "contact_id": contact.get("Id")}
            else:
                logger.info(f"Verificación por teléfono fallida para: {full_name}")
                tool_context.state[State.Case.CLIENT_VERIFIED] = False
                return {"status": "success", "verified": False, "message": data.get("message")}

    except httpx.RequestError as e:
        message = f"Error de conexión durante la verificación por teléfono: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": "No se pudo conectar al servicio de la API."}
    except Exception as e:
        message = f"Ocurrió un error inesperado durante la verificación por teléfono: {e}"
        logger.error(message)
        tool_context.state[State.Case.CLIENT_VERIFIED] = False
        return {"status": "error", "message": message}

def create_customer_service(
    call_type: str,
    relationship: str,
    fast_note: str,
    last_help_year: str,
    channel: str,
    client_type: str,
    mood: str,
    tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Crea un nuevo registro de servicio al cliente (Customer_Service__c) en Salesforce.
    Esta herramienta debe usarse después de que el cliente ha sido verificado y se necesita registrar la interacción.
    """
    account_id = tool_context.state.get(State.Account.ID)
    if not account_id:
        message = "No se encontró un 'AccountId' en el estado. No se puede crear el servicio al cliente."
        logger.error(message)
        return {"status": "error", "message": message}

    payload = {
        "AccountId": account_id,
        "CallType__c": call_type,
        "ParentezcoDelCliente__c": relationship,
        "Fast_Note__c": fast_note,
        "UltimoAnioDeAyuda__c": last_help_year,
        "Communication_channel__c": channel,
        "TipoCliente__c": client_type,
        "TipoHumor_Cliente__c": mood
    }

    logger.info(f"Intentando crear registro de servicio al cliente con payload: {payload}")
    try:
        auth_token = _get_auth_token(BASE_URL_SALESFORCE_API)
        headers = {"Authorization": f"Bearer {auth_token}"}

        with httpx.Client() as client:
            response = client.post(
                f"{BASE_URL_SALESFORCE_API}/customer_service/create",
                json=payload,
                headers=headers,
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()

            if data.get("status") == "created":
                service_record = data.get("customer_service", {})
                service_id = service_record.get("Id")
                logger.info(f"Registro de servicio al cliente creado exitosamente con ID: {service_id}")
                return {"status": "success", "created": True, "service_id": service_id, "service_data": service_record}
            else:
                error_message = data.get("message", "Error desconocido de la API al crear el servicio.")
                logger.error(f"La API devolvió un error lógico al crear el servicio: {error_message}")
                return {"status": "error", "message": error_message, "details": data.get("details")}

    except httpx.RequestError as e:
        message = f"Error de conexión al crear el servicio al cliente: {e}"
        logger.error(message)
        return {"status": "error", "message": "No se pudo conectar al servicio de la API."}
    except Exception as e:
        message = f"Ocurrió un error inesperado al crear el servicio al cliente: {e}"
        logger.error(message)
        return {"status": "error", "message": message}

class SalesforceToolset(BaseToolset):
    """
    Un toolset para interactuar con la API de Salesforce.
    """
    def __init__(self, prefix: str = "salesforce_"):
        super().__init__()
        self.prefix = prefix

        def _find_wrapper(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
            return find_contact_by_name(full_name=full_name, tool_context=tool_context)
        _find_wrapper.__name__ = f"{self.prefix}find_contact_by_name"
        _find_wrapper.__doc__ = find_contact_by_name.__doc__

        def _create_wrapper(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
            return create_contact(full_name=full_name, tool_context=tool_context)
        _create_wrapper.__name__ = f"{self.prefix}create_contact"
        _create_wrapper.__doc__ = create_contact.__doc__

        def _verify_wrapper(full_name: str, dob: str, tool_context: ToolContext) -> Dict[str, Any]:
            return verify_contact_by_dob(full_name=full_name, dob=dob, tool_context=tool_context)
        _verify_wrapper.__name__ = f"{self.prefix}verify_contact_by_dob"
        _verify_wrapper.__doc__ = verify_contact_by_dob.__doc__

        def _verify_phone_wrapper(full_name: str, dob: str, phone: str, tool_context: ToolContext) -> Dict[str, Any]:
            return verify_contact_by_dob_phone(full_name=full_name, dob=dob, phone=phone, tool_context=tool_context)
        _verify_phone_wrapper.__name__ = f"{self.prefix}verify_contact_by_dob_phone"
        _verify_phone_wrapper.__doc__ = verify_contact_by_dob_phone.__doc__

        def _create_service_wrapper(
            call_type: str,
            relationship: str,
            fast_note: str,
            last_help_year: str,
            channel: str,
            client_type: str,
            mood: str,
            tool_context: ToolContext
        ) -> Dict[str, Any]:
            return create_customer_service(
                call_type=call_type,
                relationship=relationship,
                fast_note=fast_note,
                last_help_year=last_help_year,
                channel=channel,
                client_type=client_type,
                mood=mood,
                tool_context=tool_context
            )
        _create_service_wrapper.__name__ = f"{self.prefix}create_customer_service"
        _create_service_wrapper.__doc__ = create_customer_service.__doc__

        self.tools = [
            FunctionTool(func=_find_wrapper),
            FunctionTool(func=_create_wrapper),
            FunctionTool(func=_verify_wrapper),
            FunctionTool(func=_verify_phone_wrapper),
            FunctionTool(func=_create_service_wrapper)
        ]

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        return self.tools

    async def close(self) -> None:
        pass