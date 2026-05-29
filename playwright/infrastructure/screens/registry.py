"""
SCREEN_HANDLER_REGISTRY — mapeamento de screen_id → handler concreto.

Análogo ao ACTION_REGISTRY em actions/registry.py, mas para telas.
Cada entrada associa um screen_id (definido no YAML de specs/screens/)
ao seu handler concreto que encapsula comportamentos específicos da tela.

Como adicionar uma nova tela:
    1. Crie specs/screens/<nome_da_tela>.yaml  (anchors + regions)
    2. Crie infrastructure/screens/<nome_da_tela>_handler.py
       herdando de BaseScreenHandler
    3. Adicione ao dicionário abaixo:
           from infrastructure.screens.<nome_da_tela>_handler import NomeDaTelaHandler
           SCREEN_HANDLER_REGISTRY["<nome_da_tela>"] = NomeDaTelaHandler()

Telas sem handler registrado continuam funcionando normalmente —
o handler é opcional e puramente aditivo.
"""

from application.ports import AbstractScreenHandler

# Registre os handlers das telas aqui à medida que forem implementados.
# Exemplo (descomente e adapte quando as telas estiverem prontas):
#
# from infrastructure.screens.menu_principal_handler import MenuPrincipalHandler
# from infrastructure.screens.tela_gsfat_handler import TelaGsfatHandler
#
# SCREEN_HANDLER_REGISTRY: dict[str, AbstractScreenHandler] = {
#     "menu_principal": MenuPrincipalHandler(),
#     "tela_gsfat":     TelaGsfatHandler(),
# }

SCREEN_HANDLER_REGISTRY: dict[str, AbstractScreenHandler] = {}
