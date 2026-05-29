import pytest

from domain.entities import ScreenSpec
from domain.services import StateMachine
from domain.value_objects import ScreenRegion


@pytest.fixture
def screen_specs():
    menu_spec = ScreenSpec(
        id="menu_principal",
        anchors=["Menu Protheus", "Home"],
        regions={
            "search_box": ScreenRegion("search_box", 10, 20, 100, 30)
        }
    )
    gsfat_spec = ScreenSpec(
        id="tela_gsfat",
        anchors=["Faturamento", "Rotina de Corte"],
        regions={
            "corte_grid": ScreenRegion("corte_grid", 50, 100, 500, 300)
        }
    )
    return {
        "menu": menu_spec,
        "gsfat": gsfat_spec
    }


def test_state_machine_initialization():
    sm = StateMachine()
    assert sm.current_screen is None
    assert sm.get_current_spec() is None


def test_state_machine_register(screen_specs):
    sm = StateMachine()
    sm.register(screen_specs["menu"])

    assert sm.get_spec("menu_principal") == screen_specs["menu"]
    assert sm.get_spec("tela_gsfat") is None


def test_state_machine_transition_valid(screen_specs):
    sm = StateMachine()
    sm.register(screen_specs["menu"])
    sm.register(screen_specs["gsfat"])

    sm.transition_to("menu_principal")
    assert sm.current_screen == "menu_principal"
    assert sm.is_at("menu_principal")
    assert not sm.is_at("tela_gsfat")
    assert sm.get_current_spec() == screen_specs["menu"]

    sm.transition_to("tela_gsfat")
    assert sm.current_screen == "tela_gsfat"
    assert sm.is_at("tela_gsfat")
    assert sm.get_current_spec() == screen_specs["gsfat"]


def test_state_machine_transition_invalid(screen_specs):
    sm = StateMachine()
    sm.register(screen_specs["menu"])

    with pytest.raises(ValueError) as excinfo:
        sm.transition_to("tela_gsfat")

    assert "Tela desconhecida: 'tela_gsfat'" in str(excinfo.value)
    assert sm.current_screen is None
