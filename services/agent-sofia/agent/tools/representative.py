from typing import Any, Dict, List, Optional

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset

from .states import State


def extract_full_name(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
    """
    Extrae y guarda el nombre completo del **representante**, es decir, la persona que está realizando la llamada.
    Usa esta herramienta para capturar el nombre de la persona que dice "yo soy", "mi nombre es", o se identifica como el interlocutor.
    Ejemplo: Si el usuario dice "Soy Carlos y llamo por Ana Pérez", el valor para esta herramienta es "Carlos".
    También divide el nombre completo en nombre y apellido y los guarda por separado.
    Marca que el interlocutor es un representante.
    """
    tool_context.state[State.Representative.IS_REPRESENTATIVE] = True
    tool_context.state[State.Representative.FULL_NAME] = full_name
    rep_parts = full_name.strip().split()
    rep_first_name = rep_parts[0] if rep_parts else ""
    rep_last_name = " ".join(rep_parts[1:]) if len(rep_parts) > 1 else ""

    tool_context.state[State.Representative.FIRST_NAME] = rep_first_name
    tool_context.state[State.Representative.LAST_NAME] = rep_last_name

    if rep_first_name and rep_last_name:
        tool_context.state[State.Representative.NAME_GATHERED] = True
    else:
        tool_context.state[State.Representative.NAME_GATHERED] = False

    return {
        "status": "success",
        "saved_data": {
            "representative_name": full_name,
        },
    }


def extract_relationship(relationship: str, tool_context: ToolContext) -> Dict[str, Any]:
    """Extrae y guarda el parentesco o relación del representante con el cliente."""
    tool_context.state[State.Representative.RELATIONSHIP] = relationship
    tool_context.state[State.Representative.RELATIONSHIP_GATHERED] = True
    return {"status": "success", "saved_data": {"relationship": relationship}}


def reset_search(tool_context: ToolContext) -> Dict[str, Any]:
    """
    Reinicia el indicador de búsqueda de cliente.
    Debe usarse cuando una búsqueda inicial falla y se le pregunta al usuario si es un representante,
    para permitir que el ReceptionAgent procese la nueva información.
    """
    tool_context.state[State.Case.CLIENT_SEARCH_ATTEMPTED] = False
    # También limpiamos el nombre anterior para evitar confusiones
    tool_context.state[State.Personal.FULL_NAME] = None
    tool_context.state[State.Personal.FIRST_NAME] = None
    tool_context.state[State.Personal.LAST_NAME] = None
    tool_context.state[State.Personal.NAME_GATHERED] = False
    return {"status": "success", "message": "Indicador de búsqueda reiniciado."}


class RepresentativeToolset(BaseToolset):
    """
    A toolset for handling interactions with a client's representative.
    """

    def __init__(self, prefix: str = "representative_"):
        super().__init__()
        self.prefix = prefix

        def _name_wrapper(full_name: str, tool_context: ToolContext) -> Dict[str, Any]:
            return extract_full_name(full_name=full_name, tool_context=tool_context)

        _name_wrapper.__name__ = f"{self.prefix}extract_full_name"
        _name_wrapper.__doc__ = extract_full_name.__doc__

        def _relationship_wrapper(relationship: str, tool_context: ToolContext) -> Dict[str, Any]:
            return extract_relationship(relationship=relationship, tool_context=tool_context)

        _relationship_wrapper.__name__ = f"{self.prefix}extract_relationship"
        _relationship_wrapper.__doc__ = extract_relationship.__doc__

        def _reset_wrapper(tool_context: ToolContext) -> Dict[str, Any]:
            return reset_search(tool_context=tool_context)

        _reset_wrapper.__name__ = f"{self.prefix}reset_search"
        _reset_wrapper.__doc__ = reset_search.__doc__

        self.tools = [
            FunctionTool(func=_name_wrapper),
            FunctionTool(func=_relationship_wrapper),
            FunctionTool(func=_reset_wrapper),
        ]

    async def get_tools(self, readonly_context: Optional[ReadonlyContext] = None) -> List[BaseTool]:
        return self.tools

    async def close(self) -> None:
        pass