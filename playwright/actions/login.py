"""
login — abre o Protheus e faz autenticação com credenciais do .env.
"""

import logging
from typing import Any

from actions.base import BaseAction
from settings import settings

log = logging.getLogger(__name__)


class LoginAction(BaseAction):
    def execute(self, params: dict[str, Any], context: dict[str, Any]) -> None:
        url = params.get("url", settings.PROTHEUS_URL)
        initial_program = params.get("initial_program", settings.PROTHEUS_INITIAL_PROGRAM)
        server_environment = params.get(
            "server_environment",
            settings.PROTHEUS_SERVER_ENVIRONMENT,
        )
        user = params.get("user", settings.PROTHEUS_USER)
        password = params.get("password", settings.PROTHEUS_PASSWORD)

        log.info("[login] Abrindo URL: %s", url)
        self.session.open(url)

        log.info(
            "[login] Autenticando (user=%s, program=%s, env=%s)",
            user,
            initial_program,
            server_environment,
        )
        self.session.login(
            user=user,
            password=password,
            initial_program=initial_program,
            server_environment=server_environment,
        )
        log.info("[login] Autenticação concluída — aguardando tela de Boas-vindas")

        welcome_text = "Boas-vindas"
        self.session.wait_for_text_visible(welcome_text, timeout_ms=15000)
        log.info("[login] Tela de Boas-vindas visível")

        self.session.dismiss_overlay_if_present()

        log.info("[login] Clicando no botão Entrar")
        self.session.click_entrar_button()
        log.info("[login] Botão Entrar clicado — aguardando possíveis modais")

        # Pequena espera para dar tempo do modal de ambiente aparecer
        import time

        time.sleep(2)

        log.info("[login] Consumindo overlays pós-login")
        for attempt in range(5):
            closed = self.session.dismiss_overlay_if_present()
            if not closed:
                log.info("[login] Sem overlays adicionais após %d tentativa(s)", attempt + 1)
                break
            log.info("[login] Overlay %d fechado", attempt + 1)

        log.info("[login] LoginAction concluída; fluxo de navegação segue no workflow")
