from contextlib import suppress
from typing import Any

from actions.base import BaseAction


class WaitScreenAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        screen_id = params.get("screen", "")

        # Busca a spec pelo screen_id alvo, nao pela tela atual.
        screen_spec = self.sm.get_spec(screen_id) if self.sm and screen_id else None

        # Valida os anchors visiveis para confirmar que estamos na tela certa.
        if screen_spec and screen_spec.anchors:
            for anchor in screen_spec.anchors:
                self.session.wait_for_text_visible(anchor, timeout_ms=20_000)
        else:
            # Fallback: aguarda o estado de pronto da aplicacao.
            self.session.wait_for_app_ready()

        if self.sm and screen_id:
            with suppress(ValueError):
                self.sm.transition_to(screen_id)

        # Notifica o handler da tela, se registrado
        if screen_id and screen_id in self.screen_handlers:
            self.screen_handlers[screen_id].on_enter(context, self.session)
