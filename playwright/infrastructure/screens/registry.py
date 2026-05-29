"""
SCREEN_HANDLER_REGISTRY faz o mapeamento de screen_id para handler concreto.

E analogo ao ACTION_REGISTRY em actions/registry.py, mas para telas.
Cada entrada associa um screen_id, definido no YAML de specs/screens,
ao handler concreto que encapsula comportamentos especificos da tela.

Como adicionar uma nova tela:
    1. Crie specs/screens/<nome_da_tela>.yaml  (anchors + regions)
    2. Crie infrastructure/screens/<nome_da_tela>_handler.py
       herdando de BaseScreenHandler
   3. Adicione ao dicionario abaixo:
           from infrastructure.screens.<nome_da_tela>_handler import NomeDaTelaHandler
           SCREEN_HANDLER_REGISTRY["<nome_da_tela>"] = NomeDaTelaHandler()

Telas sem handler registrado continuam funcionando normalmente.
O handler e opcional e puramente aditivo.
"""

from application.ports import AbstractScreenHandler

# Registre os handlers das telas aqui a medida que forem implementados.
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
