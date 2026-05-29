"""
search_routine — usa a barra de pesquisa do Protheus webapp
para localizar e abrir uma rotina pelo nome.

Spec YAML:
  - action: search_routine
    value: "Rotina de Corte"
"""

from typing import Any

from actions.base import BaseAction


class SearchRoutineAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        routine_name = params.get("value", "")
        if not routine_name:
            raise ValueError("search_routine requer o parâmetro 'value' com o nome da rotina.")

        self.session.search_and_open_routine(routine_name)
