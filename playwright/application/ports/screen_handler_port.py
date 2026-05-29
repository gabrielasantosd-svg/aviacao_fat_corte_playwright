"""
AbstractScreenHandler - port para handlers de tela especifica.

Cada tela da aplicacao pode ter um handler concreto que encapsula
comportamentos e interacoes exclusivos daquela tela.

Quando o workflow executa wait_screen e transiciona para uma tela,
o handler correspondente, se registrado, recebe a notificacao on_enter.
Quando sai da tela, on_exit e chamado.

Isso permite isolar logica de tela, como validacoes e extracoes de dados
padronizadas, sem poluir as actions genericas ou o workflow YAML.

Como adicionar uma nova tela:
    1. Crie o YAML em specs/screens/<nova_tela>.yaml
    2. Crie uma subclasse de BaseScreenHandler em infrastructure/screens/
    3. Registre no SCREEN_HANDLER_REGISTRY em infrastructure/screens/registry.py
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from application.ports.session_port import AbstractBrowserSession


class AbstractScreenHandler(ABC):
    """Port: comportamento especifico de uma tela da UI."""

    @property
    @abstractmethod
    def screen_id(self) -> str:
        """Identificador unico da tela; deve corresponder ao ScreenSpec.id do YAML."""
        ...

    def on_enter(
        self,
        context: dict[str, Any],
        session: "AbstractBrowserSession",
    ) -> None:
        """Chamado logo apos a state machine transicionar para esta tela.

        Use para: validacoes extras de ancoras, extracao de dados da tela,
        setup de contexto compartilhado entre steps.
        """
        _ = (context, session)

    def on_exit(
        self,
        context: dict[str, Any],
        session: "AbstractBrowserSession",
    ) -> None:
        """Chamado antes da state machine sair desta tela.

        Use para: limpeza de estado, logging e captura de screenshots de saida.
        """
        _ = (context, session)
