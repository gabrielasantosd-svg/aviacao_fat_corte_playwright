"""
BaseScreenHandler — implementação base concreta de AbstractScreenHandler.

Herde esta classe para criar handlers de telas específicas da UI.
Apenas sobrescreva os métodos relevantes para aquela tela.

Exemplo de uso para uma nova tela "pedidos":
──────────────────────────────────────────────────────────────
    # infrastructure/screens/pedidos_handler.py

    from infrastructure.screens.base_screen_handler import BaseScreenHandler
    from application.ports import AbstractBrowserSession


    class PedidosHandler(BaseScreenHandler):
        screen_id = "pedidos"

        def on_enter(self, context, session: AbstractBrowserSession) -> None:
            # Extrai o número do pedido visível e armazena no contexto
            numero = session.wait_and_extract_text(".numero-pedido")
            context["numero_pedido"] = numero

    # Em infrastructure/screens/registry.py:
    from infrastructure.screens.pedidos_handler import PedidosHandler
    SCREEN_HANDLER_REGISTRY["pedidos"] = PedidosHandler()
──────────────────────────────────────────────────────────────
"""

from typing import Any

from application.ports import AbstractBrowserSession, AbstractScreenHandler


class BaseScreenHandler(AbstractScreenHandler):
    """Base concreta para handlers de tela.

    Fornece implementações no-op de on_enter/on_exit.
    Subclasses definem `screen_id` como atributo de classe e sobrescrevem
    apenas os hooks necessários.
    """

    # Subclasses devem redefinir como atributo de classe:
    #   screen_id = "nome_da_tela"
    _screen_id: str = ""

    @property
    def screen_id(self) -> str:
        if not self._screen_id:
            raise NotImplementedError(
                f"{type(self).__name__} deve definir o atributo de classe 'screen_id'."
            )
        return self._screen_id

    def on_enter(
        self,
        context: dict[str, Any],
        session: AbstractBrowserSession,
    ) -> None:
        """Hook chamado ao entrar na tela. Sobrescreva conforme necessário."""

    def on_exit(
        self,
        context: dict[str, Any],
        session: AbstractBrowserSession,
    ) -> None:
        """Hook chamado ao sair da tela. Sobrescreva conforme necessário."""
