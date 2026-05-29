from abc import ABC, abstractmethod


class AbstractBrowserSession(ABC):
    """Port: operações de browser sem acoplamento a Playwright."""

    @abstractmethod
    def open(self, url: str) -> None: ...

    @abstractmethod
    def close(self) -> None: ...

    @abstractmethod
    def screenshot(self) -> bytes: ...

    @abstractmethod
    def click_selector(self, selector: str) -> None: ...

    @abstractmethod
    def type_text(self, selector: str, text: str) -> None: ...

    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def find_text(self, text: str) -> bool: ...

    @abstractmethod
    def get_element_text(self, selector: str) -> str: ...

    # ── Métodos de alto nível (Protheus-specific helpers) ─────────────

    @abstractmethod
    def login(
        self,
        user: str,
        password: str,
        initial_program: str = "",
        server_environment: str = "",
    ) -> None:
        """Realiza o fluxo de autenticação completo."""
        ...

    @abstractmethod
    def wait_for_text_visible(self, text: str, timeout_ms: int = 20_000) -> None:
        """Aguarda até o texto aparecer na tela."""
        ...

    @abstractmethod
    def click_text(self, text: str) -> None:
        """Localiza e clica em um elemento pelo texto visível."""
        ...

    @abstractmethod
    def search_and_open_routine(self, routine_name: str) -> None:
        """Usa a barra de pesquisa do Protheus para abrir uma rotina."""
        ...

    @abstractmethod
    def wait_and_extract_text(self, selector: str) -> str:
        """Aguarda o seletor estar disponível e extrai seu texto."""
        ...

    @abstractmethod
    def wait_for_app_ready(self) -> None:
        """Aguarda o estado de pronto da aplicação (spinner, networkidle, etc.)."""
        ...

    @abstractmethod
    def click_entrar_button(self) -> None:
        """Clica no botão 'Entrar' da tela de boas-vindas/seleção de empresa."""
        ...

    @abstractmethod
    def dismiss_overlay_if_present(self) -> bool:
        """Detecta e fecha telas sobrepostas (modais/avisos) inesperadas.

        Retorna True se alguma sobreposição foi fechada, False caso contrário.
        """
        ...
