from .states import State
from typing import Any, Dict, List, Optional
import re
import datetime
import dateparser
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset

def extract_full_name(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extrae y guarda el nombre completo del **cliente final**, la persona sobre la cual es la consulta.
    Si alguien llama en nombre de otra persona (un representante), este es el nombre de la persona representada.
    Ejemplo: Si el usuario dice "Soy Carlos y llamo por Ana Pérez", el valor para esta herramienta es "Ana Pérez".
    También divide el nombre completo en nombre y apellido y los guarda por separado.
    Si se proporciona un nombre completo (nombre y apellido), marca que el nombre ha sido recopilado.
    """
    tool_context.state[State.Customer.FULL_NAME] = full_name
    parts = full_name.strip().split()
    first_name = parts[0] if parts else ""
    last_name = " ".join(parts[1:]) if len(parts) > 1 else ""

    tool_context.state[State.Customer.FIRST_NAME] = first_name
    tool_context.state[State.Customer.LAST_NAME] = last_name

    # Solo marcar como recopilado si tenemos nombre y apellido.
    if first_name and last_name:
        tool_context.state[State.Customer.NAME_GATHERED] = True
    else:
        tool_context.state[State.Customer.NAME_GATHERED] = False

    return {"status": "success", "saved_data": {"full_name": full_name, "first_name": first_name, "last_name": last_name}}

def extract_dob(dob: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extrae, valida y normaliza la fecha de nacimiento (DOB) del cliente a formato YYYY-MM-DD.
    Intenta interpretar varios formatos de fecha comunes, incluyendo formatos en lenguaje natural en español.
    """
    # Usar dateparser para interpretar la fecha en español.
    # 'es' para español. DATE_ORDER='DMY' ayuda a resolver ambigüedades como 01/02/2000.
    parsed_date = dateparser.parse(dob, languages=['es'], settings={'DATE_ORDER': 'DMY'})

    if parsed_date:
        # Normalizamos la fecha al formato YYYY-MM-DD, que es el que espera la API.
        normalized_dob = parsed_date.strftime('%Y-%m-%d')
        tool_context.state[State.Customer.DOB] = normalized_dob
        return {"status": "success", "saved_data": {"dob": normalized_dob}}
    else:
        # Si ningún formato funcionó, devolvemos un error.
        return {"status": "error", "message": "No pude entender el formato de la fecha. ¿Podrías proporcionarla de nuevo, por ejemplo, como '1995-08-23' o '23 de agosto de 1995'?"}

def extract_phone_number(phone: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extrae y normaliza el número de teléfono del cliente.
    Guarda solo los dígitos.
    """
    # Normaliza el número de teléfono quitando todo lo que no sea un dígito.
    normalized_phone = re.sub(r'\D', '', phone)
    if len(normalized_phone) < 7: # Validación básica de longitud.
        return {"status": "error", "message": "El número de teléfono parece ser muy corto. Por favor, proporciónalo de nuevo."}
    
    tool_context.state[State.Customer.PHONE] = normalized_phone
    return {"status": "success", "saved_data": {"phone": normalized_phone}}

class CustomerDataToolset(BaseToolset):
    """
    A toolset for extracting and saving personal data.
    """

    def __init__(self, prefix: str = "customer_"):
        self.prefix = prefix

        def _name_wrapper(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
            return extract_full_name(full_name=full_name, tool_context=tool_context)
        _name_wrapper.__name__ = f"{self.prefix}extract_full_name"
        _name_wrapper.__doc__ = extract_full_name.__doc__

        def _dob_wrapper(dob: str, tool_context: ToolContext) -> Dict[str, Any]:
            return extract_dob(dob=dob, tool_context=tool_context)
        _dob_wrapper.__name__ = f"{self.prefix}extract_dob"
        _dob_wrapper.__doc__ = extract_dob.__doc__

        def _phone_wrapper(phone: str, tool_context: ToolContext) -> Dict[str, Any]:
            return extract_phone_number(phone=phone, tool_context=tool_context)
        _phone_wrapper.__name__ = f"{self.prefix}extract_phone_number"
        _phone_wrapper.__doc__ = extract_phone_number.__doc__

        self.tools = [
            FunctionTool(func=_name_wrapper),
            FunctionTool(func=_dob_wrapper),
            FunctionTool(func=_phone_wrapper),
        ]
    
    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        return self.tools
    async def close(self) -> None:
        pass
