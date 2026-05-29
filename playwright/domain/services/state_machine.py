"""StateMachine rastreia a tela atual da sessao Protheus.

Nao depende de infraestrutura: recebe dados ja processados.
"""

from dataclasses import dataclass, field

from domain.entities import ScreenSpec


@dataclass
class StateMachine:
    current_screen: str | None = None
    _registry: dict[str, ScreenSpec] = field(default_factory=dict)

    def register(self, spec: ScreenSpec) -> None:
        self._registry[spec.id] = spec

    def transition_to(self, screen_id: str) -> None:
        if screen_id not in self._registry:
            raise ValueError(f"Tela desconhecida: '{screen_id}'")
        self.current_screen = screen_id

    def is_at(self, screen_id: str) -> bool:
        return self.current_screen == screen_id

    def get_current_spec(self) -> ScreenSpec | None:
        if self.current_screen:
            return self._registry.get(self.current_screen)
        return None

    def get_spec(self, screen_id: str) -> ScreenSpec | None:
        """Retorna a spec de uma tela pelo id, independente da tela atual."""
        return self._registry.get(screen_id)
