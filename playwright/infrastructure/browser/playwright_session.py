"""Implementacao concreta de AbstractBrowserSession com Playwright.

Controla o Protheus webapp via Chromium.
Cada instancia representa um contexto isolado por worker.
"""

from __future__ import annotations

import logging
from typing import Any, cast
import time

from playwright.sync_api import (
    Browser,
    BrowserContext,
    Frame,
    Page,
    Playwright,
    sync_playwright,
)

from application.ports import AbstractBrowserSession

log = logging.getLogger(__name__)

# Seletores do Protheus webapp
# Ajuste aqui caso o HTML mude entre versoes do TOTVS Cloud.

_SEL_USER_INPUT = "input#user, input[name='user'], input[name='login'], input[placeholder*='usuário' i], input[placeholder*='user' i], input[placeholder*='sobrenome' i]"
_SEL_PASS_INPUT = "input#password, input[name='password'], input[type='password']"
_SEL_LOGIN_BTN = "button[type='submit'], button:has-text('Entrar'), button:has-text('Login')"
_SEL_INITIAL_PROGRAM_INPUT = (
    "input[name*='program' i], "
    "input[id*='program' i], "
    "input[placeholder*='programa' i], "
    "input[aria-label*='programa' i]"
)
_SEL_SERVER_ENV_INPUT = (
    "input[name*='ambiente' i], "
    "input[id*='ambiente' i], "
    "input[name*='server' i], "
    "input[id*='server' i], "
    "input[placeholder*='ambiente' i], "
    "input[placeholder*='servidor' i], "
    "input[aria-label*='ambiente' i]"
)
_SEL_INITIAL_OK_BTN = (
    "button:has-text('OK'), button:has-text('Ok'), input[type='button'][value='OK']"
)
_SEL_INITIAL_TEXT_INPUTS = "input[type='text']"
# Seletor para o campo de pesquisa, priorizando o componente TOTVS.
_SEL_SEARCH_INPUT = (
    "wa-dialog[opened] wa-text-input input, "
    "wa-dialog[opened] input[type='text'], "
    "wa-text-input[placeholder*='Pesquisar' i] input, "
    "wa-text-input input[placeholder*='Pesquisar' i], "
    "input.search-input, "
    "input[placeholder*='Pesquisar' i], "
    "input[placeholder*='Search' i], "
    "input[aria-label*='Pesquisar' i], "
    "#globalSearchInput, "
    ".po-search input"
)
_SEL_SEARCH_TRIGGER = (
    "wa-text-input[placeholder*='Pesquisar' i] button, "
    "button.search-button, "
    "button[aria-label*='Pesquisar' i], "
    "wa-text-input button.button-image, "
    ".search-icon, "
    "po-search button"
)
_SEL_RESULTS_DIALOG = "wa-dialog[opened][title*='Resultados da pesquisa' i], wa-dialog[opened]:has-text('Resultados da pesquisa')"
_SEL_RESULTS_LOCALIZE_INPUT = (
    "wa-text-input#COMP4515 input, "
    "wa-text-input[name='cGet'] input, "
    "input[placeholder=''], "
    "wa-text-input input"
)
_SEL_RESULTS_LOOKUP_TRIGGER = (
    "wa-image#COMP4516, "
    "wa-image[src*='fwstd_lookup'], "
    "wa-image[src*='lookup']"
)
_SEL_MENU_ITEM = ".po-menu-item, .menu-item, li[role='menuitem']"
_SEL_LOADING_SPIN = ".po-loading-overlay, .thf-loading, .loading-mask"

# Overlays e modais a fechar automaticamente
# Adicione aqui fragmentos de texto que identificam avisos indesejados.
_KNOWN_OVERLAY_TEXTS = [
    "base de Desenvolvimento",
    "ambiente de Producao nao e recomendado",
    "Este ambiente utiliza",
    "Moedas",
    "Limite de conexoes excedidos",
]

# Seletores para botoes de fechar em modais conhecidos, restritos ao modal.
_OVERLAY_CLOSE_SELECTORS = [
    "po-modal button.po-modal-close",
    ".po-modal-close button",
    ".po-modal-close",
    "po-modal button:has-text('OK')",
    "po-modal button:has-text('Fechar')",
    "po-modal button:has-text('Confirmar')",
    ".po-modal-footer button",
    "button.po-icon-close",
    "button[aria-label*='fechar' i]",
    "button[aria-label*='close' i]",
    "button:has-text('OK')",
    "button:has-text('Fechar')",
    "button:has-text('Confirmar')",
    "button:has-text('Finalizar')",
]

# Seletores estruturais que identificam qualquer modal ou overlay visivel no PO-UI/TOTVS,
# independentemente do conteudo de texto, para overlays desconhecidos.
_GENERIC_OVERLAY_SELECTORS = [
    "wa-dialog[opened]",  # TOTVS WebApp dialogs
    "po-modal[ng-reflect-hide='false']",
    "po-modal.po-modal-active",
    "po-modal:visible",
    ".po-modal-overlay:visible",
    "div[class*='modal'][class*='active']:visible",
    "div[role='dialog']:visible",
    "[aria-modal='true']:visible",
    ".po-modal:visible",
    "thf-modal:visible",
]

# Botoes de fechar dentro de um overlay generico detectado estruturalmente.
_GENERIC_OVERLAY_CLOSE_SELECTORS = [
    "wa-button[caption*='Fechar' i]",  # TOTVS WebApp buttons
    "wa-button[caption*='OK' i]",
    "wa-button:has-text('Fechar')",
    "wa-button:has-text('OK')",
    "button.po-modal-close",
    ".po-modal-close",
    "button.po-icon-close",
    "button[aria-label*='fechar' i]",
    "button[aria-label*='close' i]",
    ".po-modal-footer button:first-child",
    ".po-modal-footer button",
    "button:has-text('OK')",
    "button:has-text('Fechar')",
    "button:has-text('Confirmar')",
    "button:has-text('Entendido')",
    "button:has-text('Ciente')",
    "button:has-text('Continuar')",
    "button:has-text('Finalizar')",
    "button:has-text('Close')",
]


class PlaywrightSession(AbstractBrowserSession):
    def __init__(self, headless: bool = False, timeout_ms: int = 30_000):
        self._headless = headless
        self._timeout = timeout_ms
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page = cast(Page, None)

    # Lifecycle

    def open(self, url: str) -> None:
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=self._headless,
            args=["--start-maximized"],
        )
        self._context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,  # cert self-signed do TOTVS Cloud
        )
        self._page = self._context.new_page()
        self._page.set_default_timeout(self._timeout)
        self._page.goto(url, wait_until="domcontentloaded")

    def close(self) -> None:
        if self._context:
            self._context.close()
        if self._browser:
            self._browser.close()
        if self._pw:
            self._pw.stop()

    # AbstractBrowserSession

    def screenshot(self) -> bytes:
        return self._page.screenshot(full_page=False)

    def click_selector(self, selector: str) -> None:
        self._view().click(selector)

    def type_text(self, selector: str, text: str) -> None:
        self._view().fill(selector, text)

    def press_key(self, key: str) -> None:
        self._page.keyboard.press(key)

    def find_text(self, text: str) -> bool:
        try:
            self._view().get_by_text(text, exact=False).first.wait_for(
                state="visible", timeout=5_000
            )
            return True
        except Exception:
            return False

    def get_element_text(self, selector: str) -> str:
        return self._view().inner_text(selector)

    # Protheus-specific helpers

    def login(
        self,
        user: str,
        password: str,
        initial_program: str = "SIGAFAT",
        server_environment: str = "C5UQ0X_DEV",
    ) -> None:
        """Preenche a tela inicial do Protheus e depois autentica o usuario."""
        self._handle_initial_program_screen(initial_program, server_environment)
        view = self._wait_for_app_frame()
        view.wait_for_selector(_SEL_USER_INPUT, state="visible")
        view.fill(_SEL_USER_INPUT, user)
        view.fill(_SEL_PASS_INPUT, password)
        view.click(_SEL_LOGIN_BTN)
        self._wait_for_app_ready()

    def search_and_open_routine(self, routine_name: str) -> None:
        """
        Localiza a barra de pesquisa do Protheus, digita o nome da rotina
        e clica no primeiro resultado encontrado.

        Fluxo:
          1. Clica no icone ou botao de pesquisa, se o input estiver oculto.
          2. Digita o nome
          3. Aguarda os resultados
          4. Clica no item correspondente
        """
        log.info("[session] Iniciando busca da rotina: %s", routine_name)
        view = self._find_search_view(timeout_ms=10_000)
        log.debug("[session] View de busca localizada: %s", type(view).__name__)

        # 1. Tenta abrir a busca clicando no trigger (se existir)
        try:
            view.click(_SEL_SEARCH_TRIGGER, timeout=3_000)
            log.debug("[session] Trigger de busca clicado")
            time.sleep(0.5)
        except Exception as exc:
            log.debug("[session] Trigger de busca indisponivel; seguindo com campo visivel: %s", exc)
            pass  # Campo ja visivel, seguir em frente.

        # 2. Aguarda o input ficar visivel.
        # Se o dialogo de resultados abrir, ele passa a ser a origem correta da busca.
        input_element = self._resolve_search_input(view, timeout_ms=10_000)
        log.debug("[session] Campo de busca/localizar resolvido")

        # Evita cliques fisicos quando a UI ainda mantem overlays interceptando eventos.
        self._focus_input_without_pointer(input_element)
        time.sleep(0.2)

        # Limpa o campo de forma mais agressiva sem depender de ponteiro.
        try:
            input_element.press("Control+A")
            input_element.press("Delete")
            log.debug("[session] Campo de busca limpo via teclado")
        except Exception as exc:
            log.debug("[session] Nao foi possivel limpar campo via teclado; tentando JavaScript: %s", exc)
            pass
        time.sleep(0.2)

        # Limpa usando JavaScript como fallback
        try:
            input_element.evaluate(
                """(input) => {
                    input.value = '';
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                }"""
            )
            log.debug("[session] Campo de busca limpo via JavaScript")
        except Exception as exc:
            log.debug("[session] Limpeza via JavaScript falhou; seguindo com digitacao: %s", exc)
            pass

        time.sleep(0.3)

        # Digita caractere por caractere com delay maior
        for char in routine_name:
            self._page.keyboard.type(char, delay=180)
            time.sleep(0.05)
        log.info("[session] Texto da rotina digitado: %s", routine_name)

        time.sleep(0.7)  # Aguarda o Protheus processar a busca

        # 4. Verifica se o texto foi digitado corretamente
        try:
            typed_value = input_element.input_value()
            if typed_value != routine_name:
                log.warning(
                    "[session] Valor digitado diverge do esperado. Atual='%s' Esperado='%s'",
                    typed_value,
                    routine_name,
                )
                # Se nao digitou corretamente, tenta via JavaScript.
                input_element.evaluate(
                    """(input, value) => {
                        input.value = value;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                        input.dispatchEvent(new Event('change', { bubbles: true }));
                    }""",
                    routine_name,
                )
                log.info("[session] Valor da busca corrigido via JavaScript: %s", routine_name)
                time.sleep(0.5)
            else:
                log.debug("[session] Valor digitado validado com sucesso")
        except Exception as exc:
            log.debug("[session] Nao foi possivel validar valor digitado: %s", exc)
            pass

        # No modal "Resultados da pesquisa", o Protheus so executa a busca
        # apos clicar na lupa ao lado do campo Localizar.
        if self._click_results_lookup_if_visible():
            log.info("[session] Lupa do dialogo de resultados clicada")
        else:
            log.debug("[session] Dialogo de resultados/lupa nao visivel; seguindo fluxo normal")

        # 5. Aguarda resultados (dropdown/lista)
        result_sel = (
            f"[class*='search-result']:has-text('{routine_name}'), "
            f"[class*='result-item']:has-text('{routine_name}'), "
            f"li:has-text('{routine_name}'), "
            f".po-combo-option:has-text('{routine_name}')"
        )
        try:
            view.wait_for_selector(result_sel, state="visible", timeout=8_000)
            view.click(result_sel + " >> nth=0")
            log.info("[session] Resultado da rotina clicado: %s", routine_name)
        except Exception as exc:
            log.warning(
                "[session] Resultado da rotina nao localizado por seletor; usando Enter. Rotina='%s' Erro=%s",
                routine_name,
                exc,
            )
            # fallback: pressiona Enter e aguarda a tela carregar
            self._page.keyboard.press("Enter")

        self._wait_for_app_ready()
        log.info("[session] Busca da rotina finalizada: %s", routine_name)

    def wait_for_text_visible(self, text: str, timeout_ms: int = 15_000) -> None:
        """Aguarda texto visivel buscando em todos os frames disponiveis.

        Inclui o iframe dentro do Shadow DOM do wa-webview (Protheus Cloud).
        """
        import logging

        log = logging.getLogger(__name__)
        deadline = time.monotonic() + timeout_ms / 1000
        last_exc: Exception | None = None
        slice_ms = 1_500  # timeout por tentativa por view

        while time.monotonic() < deadline:
            for view in self._all_searchable_views():
                try:
                    view.get_by_text(text, exact=False).first.wait_for(
                        state="visible", timeout=slice_ms
                    )
                    log.debug("[session] Texto '%s' encontrado em %s", text, type(view).__name__)
                    return
                except Exception as exc:
                    last_exc = exc

        raise TimeoutError(f"Texto '{text}' nao ficou visivel em {timeout_ms}ms.") from last_exc

    def click_text(self, text: str) -> None:
        """Clica num elemento pelo texto, buscando em todos os frames (incluindo Shadow DOM)."""
        import logging
        import re

        log = logging.getLogger(__name__)
        pattern = re.compile(re.escape(text), re.IGNORECASE)

        for view in self._all_searchable_views():
            for role in ("button", "link"):
                try:
                    el = view.get_by_role(role, name=pattern)
                    el.first.wait_for(state="visible", timeout=1_500)
                    el.first.click()
                    log.debug("[session] Clicou '%s' via role=%s", text, role)
                    return
                except Exception:
                    pass
            try:
                el = view.get_by_text(text, exact=False)
                el.first.wait_for(state="visible", timeout=1_500)
                el.first.click()
                log.debug("[session] Clicou '%s' via get_by_text", text)
                return
            except Exception:
                pass

        raise RuntimeError(f"Elemento com texto '{text}' nao encontrado em nenhum frame.")

    def click_entrar_button(self) -> None:
        """Clica no botao 'Entrar' da tela de boas-vindas ou selecao de empresa.

        Arquitetura real do Protheus Cloud:
            page (main) -> wa-webview[shadowrootmode="open"]
                          -> <iframe> -> Angular/PO-UI
                              -> <button> com span.po-button-label "Entrar"

        O iframe fica dentro do Shadow DOM do wa-webview, portanto precisamos
        usar frame_locator com piercing de shadow (">>") para alcanca-lo.

        Estrategias em cascata:
          1. frame_locator("wa-webview >> iframe") + get_by_role
          2. page.frame(url pattern) + get_by_role / CSS
          3. Iteracao em page.frames com force=True
          4. JavaScript click como ultimo recurso
        """
        import re

        # Estrategia 1: frame_locator com Shadow DOM piercing.
        # Esta e a forma recomendada pelo Playwright para iframes dentro de
        # Shadow DOM (wa-webview renderiza um <iframe> no seu shadow root).
        shadow_piercing_selectors = [
            "wa-webview >> iframe",
            "wa-webview",  # Em alguns casos o proprio wa-webview aceita locator.
        ]
        for fl_sel in shadow_piercing_selectors:
            try:
                fl = self._page.frame_locator(fl_sel)
                btn = fl.get_by_role("button", name=re.compile(r"entrar", re.IGNORECASE))
                btn.first.wait_for(state="visible", timeout=5_000)
                btn.first.click()
                return
            except Exception:
                pass

            # Tenta CSS dentro do frame_locator
            for css in [
                "button:has(span.po-button-label:has-text('Entrar'))",
                "button:has(.po-button-container:has-text('Entrar'))",
                "button:has-text('Entrar')",
                "div.po-button-container:has-text('Entrar')",
                "span.po-button-label:has-text('Entrar')",
            ]:
                try:
                    el = fl.locator(css)
                    el.first.wait_for(state="visible", timeout=2_000)
                    el.first.click()
                    return
                except Exception:
                    pass

        # Estrategia 2: page.frame() por URL.
        url_patterns = ["**/app-root/**", "**/preindex**", "**/index.html**"]
        for pattern in url_patterns:
            try:
                frame = self._page.frame(url=pattern)
                if frame is None:
                    continue
                btn = frame.get_by_role("button", name=re.compile(r"entrar", re.IGNORECASE))
                btn.first.wait_for(state="visible", timeout=3_000)
                btn.first.click()
                return
            except Exception:
                pass

        # Estrategia 3: iteracao em todos os frames.
        candidates = [self._page] + list(self._page.frames)
        css_selectors = [
            "button:has(span.po-button-label:has-text('Entrar'))",
            "button:has(.po-button-container:has-text('Entrar'))",
            "button:has-text('Entrar')",
            "po-button[name='submmit'] button",
            ".session-settings-button-enter button",
        ]
        for view in candidates:
            # get_by_role normal
            try:
                btn = view.get_by_role("button", name=re.compile(r"entrar", re.IGNORECASE))
                btn.first.wait_for(state="visible", timeout=1_500)
                btn.first.click()
                return
            except Exception:
                pass
            # CSS com force=True
            for sel in css_selectors:
                try:
                    view.wait_for_selector(sel, state="attached", timeout=1_500)
                    view.locator(sel).first.click(force=True)
                    return
                except Exception:
                    pass

        # Estrategia 4: JavaScript click.
        for view in candidates:
            for js_sel in ["span.po-button-label", "div.po-button-container"]:
                try:
                    view.wait_for_selector(
                        f"{js_sel}:has-text('Entrar')", state="attached", timeout=1_000
                    )
                    el = view.locator(f"{js_sel}:has-text('Entrar')").first
                    el.evaluate(
                        "node => {"
                        "  const target = node.closest('button') || node.closest('[role=\"button\"]') || node;"
                        "  target.click();"
                        "}"
                    )
                    return
                except Exception:
                    pass

        # Falhou: salva screenshot de debug e lanca erro descritivo.
        try:
            import os

            debug_path = os.path.normpath(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..",
                    "..",
                    "..",
                    "screenshots",
                    "debug_entrar_fail.png",
                )
            )
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            self._page.screenshot(path=debug_path, full_page=True)
            print(f"[DEBUG] Screenshot salvo em: {debug_path}")
        except Exception as se:
            print(f"[DEBUG] Nao foi possivel salvar screenshot: {se}")

        raise RuntimeError(
            "Botão 'Entrar' não encontrado na tela de boas-vindas. "
            "Verifique o screenshot de debug em screenshots/debug_entrar_fail.png"
        )

    def dismiss_overlay_if_present(self) -> bool:
        """Detecta e fecha telas sobrepostas inesperadas, como avisos e modais TOTVS.

        Tres passes:
          0. wa-dialog.dict-msdialog nativo do TOTVS: usa wa-button com Shadow
             DOM, com piercing via >>, cobrindo o aviso de base de Desenvolvimento.
          1. Textos conhecidos em frames normais (PO-UI / Angular).
          2. Estrutura generica: qualquer modal ou dialogo visivel desconhecido.

        Nunca lanca excecao. Retorna True se fechou algo, False caso contrario.
        """
        try:
            # Passe 0: qualquer wa-dialog[opened] nativo do TOTVS.
            # Cobre: aviso "base de Desenvolvimento", dialog "Moedas", e outros.
            # Estrutura comum:
            #   <wa-dialog opened>
            #     <wa-button caption="Confirmar|Fechar|OK">  <- Shadow DOM
            #       #shadow-root -> <button><span>texto</span></button>
            #     </wa-button>
            #   </wa-dialog>
            try:
                # Ordena: Confirmar primeiro (para "Moedas"), depois Fechar/OK
                CAPTION_PRIORITY = ["Confirmar", "Fechar", "OK", "Ciente", "Entendido", "Continuar"]

                # Estrategia direta via JavaScript.
                # O wa-button pode estar aninhado em varios wa-panel dentro do
                # wa-dialog. O Playwright nao faz deep traversal em shadow roots
                # encadeados via locator(). JavaScript percorre tudo recursivamente.
                try:
                    closed = self._page.evaluate(
                        """(captions) => {
                            function clickBtnInShadow(root, captions) {
                                // Procura wa-button com caption matching em todo o DOM/shadow
                                for (const wb of root.querySelectorAll('wa-button')) {
                                    const cap = (wb.getAttribute('caption') || '').trim();
                                    if (captions.some(c => cap.toLowerCase() === c.toLowerCase())) {
                                        // Clica no <button> dentro do shadow root do wa-button
                                        const sr = wb.shadowRoot;
                                        const innerBtn = sr && sr.querySelector('button');
                                        if (innerBtn) { innerBtn.click(); return wb.getAttribute('caption'); }
                                    }
                                }
                                // Recursao em shadow roots de outros elementos
                                for (const el of root.querySelectorAll('*')) {
                                    if (el.shadowRoot) {
                                        const found = clickBtnInShadow(el.shadowRoot, captions);
                                        if (found) return found;
                                    }
                                }
                                return null;
                            }
                            // Apenas dentro de wa-dialog[opened]
                            const dialogs = Array.from(document.querySelectorAll('wa-dialog[opened]'));
                            // Maior z-index primeiro
                            dialogs.sort((a, b) => {
                                const za = parseInt(a.style.zIndex || '0');
                                const zb = parseInt(b.style.zIndex || '0');
                                return zb - za;
                            });
                            for (const dlg of dialogs) {
                                const found = clickBtnInShadow(dlg, captions);
                                if (found) return found;
                            }
                            return null;
                        }""",
                        CAPTION_PRIORITY,
                    )
                    if closed:
                        print(
                            f"[dismiss_overlay] wa-dialog fechado via JS deep traversal: caption='{closed}'"
                        )
                        try:
                            self._page.wait_for_timeout(500)
                        except Exception:
                            pass
                        return True
                except Exception as js_err:
                    print(f"[dismiss_overlay] JS deep traversal falhou: {js_err}")

                # Fallback: locator direto na page, sem escopo no dialog.
                # Cobre casos onde o wa-button esta acessivel diretamente.
                for close_caption in CAPTION_PRIORITY:
                    try:
                        btn_host = self._page.locator(f"wa-button[caption='{close_caption}']")
                        if btn_host.count() > 0:
                            inner_btn = btn_host.first.locator("button")
                            inner_btn.wait_for(state="visible", timeout=1_500)
                            inner_btn.click()
                            print(
                                f"[dismiss_overlay] Fechado via page.locator wa-button[caption='{close_caption}']"
                            )
                            try:
                                self._page.wait_for_timeout(400)
                            except Exception:
                                pass
                            return True
                    except Exception:
                        pass

                # Itera todos os wa-dialog abertos como fallback, caso o JS falhe.
                all_dlgs = self._page.locator("wa-dialog[opened]")
                dlg_count = all_dlgs.count()
                for i in range(dlg_count - 1, -1, -1):
                    dlg = all_dlgs.nth(i)
                    for close_caption in CAPTION_PRIORITY:
                        try:
                            btn_host = dlg.locator(f"wa-button[caption='{close_caption}']")
                            if btn_host.count() > 0:
                                inner_btn = btn_host.first.locator("button")
                                inner_btn.wait_for(state="visible", timeout=1_500)
                                inner_btn.click()
                                print(
                                    f"[dismiss_overlay] wa-dialog[{i}] fechado via wa-button[caption='{close_caption}']"
                                )
                                try:
                                    self._page.wait_for_timeout(400)
                                except Exception:
                                    pass
                                return True
                        except Exception:
                            pass
            except Exception:
                pass

            candidates = [self._page] + [f for f in self._page.frames if f != self._page.main_frame]

            # Passe 1: textos conhecidos.
            for view in candidates:
                overlay_found = False
                for text in _KNOWN_OVERLAY_TEXTS:
                    try:
                        view.get_by_text(text, exact=False).first.wait_for(
                            state="visible", timeout=800
                        )
                        overlay_found = True
                        break
                    except Exception:
                        pass

                if not overlay_found:
                    continue

                closed = self._try_close_overlay(view, _OVERLAY_CLOSE_SELECTORS, label="known")
                if closed:
                    return True
                # Detectou, mas nao fechou; continua para o passe 2.
                break

            # Passe 2: estrutura generica, para overlay desconhecido.
            for view in candidates:
                for overlay_sel in _GENERIC_OVERLAY_SELECTORS:
                    try:
                        if view.locator(overlay_sel).count() == 0:
                            continue
                        view.locator(overlay_sel).first.wait_for(state="visible", timeout=600)
                        # Ha um modal visivel; tenta tirar um screenshot de diagnostico.
                        self._save_overlay_debug_screenshot()
                        closed = self._try_close_overlay(
                            view, _GENERIC_OVERLAY_CLOSE_SELECTORS, label="unknown"
                        )
                        if closed:
                            return True
                    except Exception:
                        pass

        except Exception as exc:
            # Seguranca total: nenhuma excecao pode vazar daqui e quebrar o fluxo.
            print(f"[dismiss_overlay] Erro interno ignorado: {exc}")

        return False

    def _try_close_overlay(self, view, close_selectors: list[str], label: str) -> bool:
        """Tenta clicar em cada seletor de fechar dentro do view fornecido."""
        for sel in close_selectors:
            try:
                view.wait_for_selector(sel, state="visible", timeout=1_000)
                view.locator(sel).first.click()
                print(f"[dismiss_overlay] Sobreposicao ({label}) fechada via: {sel!r}")
                # Pequena pausa para o modal terminar de fechar
                try:
                    self._page.wait_for_timeout(500)
                except Exception:
                    pass
                return True
            except Exception:
                pass
        print(f"[dismiss_overlay] Overlay ({label}) detectado, mas nenhum botao de fechar foi encontrado.")
        return False

    def _save_overlay_debug_screenshot(self) -> None:
        """Salva screenshot de diagnostico quando um overlay desconhecido e detectado."""
        try:
            import os

            debug_path = os.path.normpath(
                os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..",
                    "..",
                    "..",
                    "screenshots",
                    "debug_unknown_overlay.png",
                )
            )
            os.makedirs(os.path.dirname(debug_path), exist_ok=True)
            self._page.screenshot(path=debug_path, full_page=False)
            print(f"[dismiss_overlay] Screenshot do overlay desconhecido salvo em: {debug_path}")
        except Exception:
            pass

    def _click_text_in_view(self, view, text: str) -> None:
        """Clica num elemento pelo texto, tentando button/link role como fallback."""
        import re

        pattern = re.compile(re.escape(text), re.IGNORECASE)
        for role in ("button", "link"):
            try:
                view.get_by_role(role, name=pattern).first.click()
                return
            except Exception:
                pass
        view.get_by_text(text, exact=False).first.click()

    def wait_and_extract_text(self, selector: str) -> str:
        view = self._view(prefer_app_frame=True)
        view.wait_for_selector(selector, state="visible")
        return view.inner_text(selector).strip()

    def wait_for_app_ready(self) -> None:
        """Implementa o port: delega para o helper interno."""
        self._wait_for_app_ready()

    # Private helpers

    def _wait_for_app_ready(self, timeout_ms: int = 20_000) -> None:
        """Aguarda o spinner de carregamento desaparecer.

        Usa 'domcontentloaded' em vez de 'networkidle' porque o Protheus Cloud
        mantem requisicoes de polling em background que nunca permitem networkidle.
        """
        try:
            self._page.wait_for_selector(_SEL_LOADING_SPIN, state="hidden", timeout=timeout_ms)
        except Exception:
            pass  # O spinner pode nao existir em todas as versoes.
        # 'domcontentloaded' e suficiente; 'networkidle' nunca e atingido no
        # Protheus Cloud por causa do polling continuo em background.
        try:
            self._page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass

    def _handle_initial_program_screen(
        self,
        initial_program: str,
        server_environment: str,
    ) -> None:
        page = self._page

        if not self._is_initial_program_screen_visible():
            return

        if not self._fill_initial_screen_by_input_order(
            initial_program=initial_program,
            server_environment=server_environment,
        ):
            self._fill_first_visible(
                [
                    _SEL_INITIAL_PROGRAM_INPUT,
                    "input:right-of(:text('Programa Inicial'))",
                ],
                initial_program,
            )
            self._fill_first_visible(
                [
                    _SEL_SERVER_ENV_INPUT,
                    "input:right-of(:text('Ambiente'))",
                    "input:right-of(:text('Servidor'))",
                ],
                server_environment,
            )

        page.click(_SEL_INITIAL_OK_BTN)
        self._wait_for_app_ready(timeout_ms=10_000)

    def _is_initial_program_screen_visible(self) -> bool:
        try:
            self._page.get_by_text("Programa Inicial", exact=False).first.wait_for(
                state="visible", timeout=5_000
            )
            return True
        except Exception:
            return False

    def _fill_first_visible(self, selectors: list[str], value: str) -> None:
        last_error: Exception | None = None
        for selector in selectors:
            try:
                self._page.wait_for_selector(selector, state="visible", timeout=3_000)
                self._page.fill(selector, value)
                return
            except Exception as exc:
                last_error = exc

        raise RuntimeError(
            f"Nao foi possivel localizar campo para preencher '{value}'."
        ) from last_error

    def _fill_initial_screen_by_input_order(
        self,
        initial_program: str,
        server_environment: str,
    ) -> bool:
        text_inputs = self._page.locator(_SEL_INITIAL_TEXT_INPUTS)
        count = text_inputs.count()
        if count < 2:
            return False

        self._replace_input_value(text_inputs.nth(0), initial_program)
        self._replace_input_value(text_inputs.nth(1), server_environment)
        return True

    def _replace_input_value(self, locator, value: str) -> None:
        locator.click()
        locator.press("Control+A")
        locator.fill(value)

    def _view(self, prefer_app_frame: bool = False) -> Page | Frame:
        app_frame = self._app_frame()
        if prefer_app_frame and app_frame is not None:
            return app_frame
        return app_frame or self._page

    def _wait_for_app_frame(self, timeout_ms: int | None = None) -> Frame:
        deadline = time.monotonic() + ((timeout_ms or self._timeout) / 1000)
        last_frame: Frame | None = None

        while time.monotonic() < deadline:
            last_frame = self._app_frame()
            if last_frame is not None:
                return last_frame
            self._page.wait_for_timeout(250)

        raise TimeoutError("App frame do Protheus nao ficou disponivel a tempo.")

    def _app_frame(self) -> Frame | None:
        if not self._page:
            return None

        for frame in reversed(self._page.frames):
            if frame == self._page.main_frame:
                continue
            if "app-root" in frame.url or "/login" in frame.url:
                return frame

        return None

    def _all_searchable_views(self) -> list[Any]:
        """Retorna todos os contextos pesquisaveis, incluindo o iframe dentro do
        Shadow DOM do wa-webview (Protheus Cloud).

        Ordem de busca:
          1. Frames normais acessiveis via page.frames, como PO-UI e telas externas.
          2. page principal
          3. frame_locator('wa-webview >> iframe') para o iframe dentro do Shadow DOM
        """
        views: list[Any] = list(self._page.frames)  # inclui main_frame e sub-frames
        if self._page not in views:
            views.insert(0, self._page)

        # Adiciona o FrameLocator que perfura o Shadow DOM do wa-webview
        for fl_sel in ("wa-webview >> iframe", "wa-webview"):
            try:
                fl = self._page.frame_locator(fl_sel)
                # FrameLocator nao e um Frame, mas suporta get_by_text e get_by_role.
                views.append(fl)
                break
            except Exception:
                pass

        return views

    def _search_candidate_views(self) -> list[Page | Frame]:
        views: list[Page | Frame] = [self._page]

        app_frame = self._app_frame()
        if app_frame is not None:
            views.append(app_frame)

        for frame in self._page.frames:
            if frame == self._page.main_frame or frame == app_frame:
                continue
            views.append(frame)

        return views

    def _find_search_view(self, timeout_ms: int = 10_000) -> Page | Frame:
        deadline = time.monotonic() + (timeout_ms / 1000)
        last_exc: Exception | None = None

        while time.monotonic() < deadline:
            if self._results_dialog_is_visible():
                return self._page

            for view in self._search_candidate_views():
                try:
                    try:
                        view.click(_SEL_SEARCH_TRIGGER, timeout=1_000)
                    except Exception:
                        pass

                    view.wait_for_selector(_SEL_SEARCH_INPUT, state="visible", timeout=1_500)
                    return view
                except Exception as exc:
                    last_exc = exc

        raise TimeoutError("Campo de pesquisa do Protheus não ficou visível a tempo.") from last_exc

    def _resolve_search_input(self, view: Page | Frame, timeout_ms: int = 10_000):
        deadline = time.monotonic() + (timeout_ms / 1000)
        last_exc: Exception | None = None

        while time.monotonic() < deadline:
            try:
                if self._results_dialog_is_visible():
                    dialog = self._page.locator(_SEL_RESULTS_DIALOG).last
                    dialog.wait_for(state="visible", timeout=1_000)
                    input_element = dialog.locator(_SEL_RESULTS_LOCALIZE_INPUT).first
                    input_element.wait_for(state="visible", timeout=1_000)
                    log.debug("[session] Campo Localizar encontrado no dialogo de resultados")
                    return input_element
            except Exception as exc:
                last_exc = exc

            try:
                view.wait_for_selector(_SEL_SEARCH_INPUT, state="visible", timeout=1_000)
                log.debug("[session] Campo de pesquisa encontrado na view atual")
                return view.locator(_SEL_SEARCH_INPUT).first
            except Exception as exc:
                last_exc = exc

        raise TimeoutError("Campo de busca não ficou visível a tempo.") from last_exc

    def _click_results_lookup_if_visible(self) -> bool:
        """Clica na lupa do dialogo 'Resultados da pesquisa', quando presente."""
        try:
            if not self._results_dialog_is_visible():
                log.debug("[session] Dialogo 'Resultados da pesquisa' nao esta visivel")
                return False

            dialog = self._page.locator(_SEL_RESULTS_DIALOG).last
            lookup = dialog.locator(_SEL_RESULTS_LOOKUP_TRIGGER).first
            lookup.wait_for(state="visible", timeout=2_000)
            log.debug("[session] Lupa do dialogo de resultados localizada")

            try:
                lookup.click(timeout=2_000)
                log.debug("[session] Lupa do dialogo clicada via click normal")
            except Exception as exc:
                log.warning("[session] Click normal na lupa falhou; tentando force=True: %s", exc)
                lookup.click(force=True, timeout=2_000)
                log.debug("[session] Lupa do dialogo clicada via force=True")

            time.sleep(0.7)
            return True
        except Exception as exc:
            log.warning("[session] Nao foi possivel clicar na lupa do dialogo de resultados: %s", exc)
            return False

    def _results_dialog_is_visible(self) -> bool:
        try:
            self._page.wait_for_selector(_SEL_RESULTS_DIALOG, state="visible", timeout=300)
            return True
        except Exception:
            return False

    def _focus_input_without_pointer(self, locator) -> None:
        try:
            locator.focus()
            return
        except Exception:
            pass

        try:
            locator.evaluate(
                """(input) => {
                    input.focus();
                    input.dispatchEvent(new Event('focus', { bubbles: true }));
                }"""
            )
        except Exception:
            pass
