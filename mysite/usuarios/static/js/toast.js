/**
 * toast(mensagem, tipo, duração_ms)
 * tipo: "erro" | "sucesso" | "aviso"   (padrão: "erro")
 * Cria um container fixo no topo e empilha toasts.
 * Cada toast some sozinho após `duracao` ms.
 * Garante que mensagens idênticas nunca apareçam simultaneamente.
 */
var mensagensAtivas = new Set();
var historicoRecente = new Map();

function toast(mensagem, tipo, duracao) {
    if (!mensagem || typeof mensagem !== "string") return;
    mensagem = mensagem.trim();
    if (!mensagem) return;

    var agora = Date.now();
    // Deduplicação: se a mesma mensagem já está em exibição ou foi exibida há menos de 2s, não cria outra
    if (mensagensAtivas.has(mensagem)) {
        return;
    }
    if (historicoRecente.has(mensagem) && (agora - historicoRecente.get(mensagem) < 2000)) {
        return;
    }
    mensagensAtivas.add(mensagem);
    historicoRecente.set(mensagem, agora);

    tipo = tipo || "erro";
    duracao = duracao || 4000;

    var container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-container";
        document.body.appendChild(container);
    }

    var el = document.createElement("div");
    el.className = "toast toast-" + tipo;
    el.textContent = mensagem;
    container.appendChild(el);

    function removerToast() {
        mensagensAtivas.delete(mensagem);
        if (el && el.parentNode) {
            el.remove();
        }
    }

    setTimeout(function() {
        el.classList.add("saindo");
        el.addEventListener("animationend", removerToast, { once: true });
        // Fallback de remoção caso animationend não seja disparado
        setTimeout(removerToast, 400);
    }, duracao);
}

/**
 * Utilitários de isolamento de sessão por aba (_user_token).
 * Impede que uma aba logada como membro/sub-líder (ex: 202409) troque repentinamente
 * para outra conta (ex: admin) ao clicar no Painel Administrativo ou em qualquer link.
 */
function ehRotaPublicaOuSaida(pathname) {
    if (!pathname) return true;
    return (
        pathname === "/" ||
        pathname === "/sair/" ||
        pathname === "/cadastro/" ||
        pathname.indexOf("/static/") === 0 ||
        pathname.indexOf("/media/") === 0
    );
}

function anexarTokenNaUrl(href, token) {
    if (!href || !token) return href;
    try {
        var url = new URL(href, window.location.origin);
        if (url.origin !== window.location.origin) return href;
        if (ehRotaPublicaOuSaida(url.pathname)) return href;
        url.searchParams.set("_user_token", token);
        return url.pathname + url.search + url.hash;
    } catch (e) {
        return href;
    }
}

function injetarTokenNoFormulario(form, token) {
    if (!form || !token) return;
    if (form.id === "form-login" || form.id === "form-cadastro") return;
    var input = form.querySelector("input[name='_user_token']");
    if (!input) {
        input = document.createElement("input");
        input.type = "hidden";
        input.name = "_user_token";
        form.appendChild(input);
    }
    input.value = token;
}

(function inicializarIsolamentoDeAbaImediato() {
    try {
        var pathAtual = window.location.pathname || "/";
        if (pathAtual === "/" || pathAtual === "/cadastro/" || pathAtual === "/sair/") {
            if (window.sessionStorage) {
                window.sessionStorage.removeItem("scripta_tab_uid");
                window.sessionStorage.removeItem("scripta_tab_token");
            }
            return;
        }
    } catch (e) {}
})();

document.addEventListener("DOMContentLoaded", function() {
    var userTokenMeta = document.querySelector("meta[name='user-token']");
    var userIdMeta = document.querySelector("meta[name='user-id']");
    var tabUserToken = userTokenMeta ? (userTokenMeta.getAttribute("content") || "").trim() : "";
    var tabUserId = userIdMeta ? (userIdMeta.getAttribute("content") || "").trim() : "";
    var pathAtual = window.location.pathname || "/";

    // Se estamos na tela de login ou cadastro, limpa qualquer vínculo anterior desta aba
    if (pathAtual === "/" || pathAtual === "/cadastro/" || !tabUserToken) {
        try {
            if (window.sessionStorage) {
                window.sessionStorage.removeItem("scripta_tab_uid");
                window.sessionStorage.removeItem("scripta_tab_token");
            }
        } catch (e) {}
    } else {
        // Verifica se esta aba já estava vinculada a outro usuário e sofreu colisão de cookie em URL sem token
        try {
            if (window.sessionStorage) {
                var storedUid = window.sessionStorage.getItem("scripta_tab_uid");
                var storedToken = window.sessionStorage.getItem("scripta_tab_token");
                var paramsAtuais = new URLSearchParams(window.location.search);
                var veioComTokenNaUrl = paramsAtuais.has("_user_token");

                if (storedUid && storedToken && tabUserId && storedUid !== tabUserId && !veioComTokenNaUrl) {
                    // A aba pertencia ao usuário `storedUid`, mas uma requisição GET sem token leu o cookie de outra aba.
                    // Restaura imediatamente a conta correta desta aba!
                    var urlCorrigida = anexarTokenNaUrl(window.location.href, storedToken);
                    window.location.replace(urlCorrigida);
                    return;
                }

                if (tabUserId && tabUserToken) {
                    window.sessionStorage.setItem("scripta_tab_uid", tabUserId);
                    window.sessionStorage.setItem("scripta_tab_token", tabUserToken);
                }
            }
        } catch (e) {}

        // Mantém o token da aba na barra de endereço (history.replaceState) para que F5/Refresh nunca troque de conta
        try {
            if (window.history && window.history.replaceState && !ehRotaPublicaOuSaida(pathAtual)) {
                var novaUrl = anexarTokenNaUrl(window.location.href, tabUserToken);
                if (novaUrl && novaUrl !== (window.location.pathname + window.location.search + window.location.hash)) {
                    window.history.replaceState(null, "", novaUrl);
                }
            }
        } catch (e) {}
    }

    // Limpa vínculo da aba ao clicar em Sair ou enviar Login
    var linkSair = document.getElementById("link-sair-sidebar");
    if (linkSair) {
        linkSair.addEventListener("click", function() {
            try {
                if (window.sessionStorage) {
                    window.sessionStorage.removeItem("scripta_tab_uid");
                    window.sessionStorage.removeItem("scripta_tab_token");
                }
            } catch (e) {}
        });
    }

    var formLogin = document.getElementById("form-login");
    if (formLogin) {
        formLogin.addEventListener("submit", function() {
            try {
                if (window.sessionStorage) {
                    window.sessionStorage.removeItem("scripta_tab_uid");
                    window.sessionStorage.removeItem("scripta_tab_token");
                }
            } catch (e) {}
        });
    }

    // Propaga o token da aba para TODOS os links internos (GET) e formulários (POST)
    if (tabUserToken) {
        document.querySelectorAll("a[href]").forEach(function(link) {
            if (link.id === "link-sair-sidebar") return;
            var rawHref = link.getAttribute("href");
            if (!rawHref || rawHref.charAt(0) === "#" || rawHref.indexOf("javascript:") === 0) return;
            link.setAttribute("href", anexarTokenNaUrl(link.href, tabUserToken));
        });

        // Listener em fase de captura para garantir que qualquer clique em link leve o _user_token da aba
        document.addEventListener("click", function(e) {
            var link = e.target && e.target.closest ? e.target.closest("a[href]") : null;
            if (!link || link.id === "link-sair-sidebar") return;
            var rawHref = link.getAttribute("href");
            if (!rawHref || rawHref.charAt(0) === "#" || rawHref.indexOf("javascript:") === 0) return;
            link.setAttribute("href", anexarTokenNaUrl(link.href, tabUserToken));
        }, true);

        document.querySelectorAll("form").forEach(function(form) {
            injetarTokenNoFormulario(form, tabUserToken);
        });

        document.addEventListener("submit", function(e) {
            if (e.target && e.target.tagName && e.target.tagName.toLowerCase() === "form") {
                injetarTokenNoFormulario(e.target, tabUserToken);
            }
        }, true);

        // Intercepta chamadas fetch() internas (como stats_painel, status_tarefa e curtir) para enviar o token da aba
        if (window.fetch && !window.__fetchComTokenInstalado) {
            var fetchOriginal = window.fetch.bind(window);
            window.__fetchComTokenInstalado = true;
            window.fetch = function(resource, init) {
                try {
                    var urlStr = (typeof resource === "string") ? resource : (resource && resource.url ? resource.url : "");
                    if (urlStr) {
                        var u = new URL(urlStr, window.location.origin);
                        if (u.origin === window.location.origin && !ehRotaPublicaOuSaida(u.pathname)) {
                            u.searchParams.set("_user_token", tabUserToken);
                            if (typeof resource === "string") {
                                resource = u.pathname + u.search + u.hash;
                            }
                            init = init ? Object.assign({}, init) : {};
                            var headers = new Headers(init.headers || {});
                            if (!headers.has("X-User-Token")) {
                                headers.set("X-User-Token", tabUserToken);
                            }
                            init.headers = headers;
                        }
                    }
                } catch (err) {}
                return fetchOriginal(resource, init);
            };
        }
    }

    // Converte elementos .msg vindos do Django no server-side em toasts sem duplicidades
    var mensagensProcessadas = new Set();

    document.querySelectorAll(".msg").forEach(function(el) {
        var tipo = el.classList.contains("msg-success") ? "sucesso"
                 : el.classList.contains("msg-error") ? "erro"
                 : "aviso";
        var msg = (el.textContent || "").trim();
        if (msg && !mensagensProcessadas.has(msg)) {
            mensagensProcessadas.add(msg);

            var chaveMsg = "toast_exibido_" + (tabUserId || "anon") + "_" + msg.replace(/\s+/g, "_").slice(0, 40);
            try {
                if (window.sessionStorage) {
                    var timestampAnterior = window.sessionStorage.getItem(chaveMsg);
                    if (timestampAnterior && (Date.now() - parseInt(timestampAnterior, 10) < 4000)) {
                        el.remove();
                        return;
                    }
                    window.sessionStorage.setItem(chaveMsg, Date.now().toString());
                }
            } catch (e) {}

            toast(msg, tipo, 4500);
        }
        el.remove();
    });

    // Se a página for restaurada do cache de navegação (bfcache), valida o usuário da aba e limpa toasts residuais
    window.addEventListener("pageshow", function(e) {
        if (e.persisted) {
            document.querySelectorAll(".msg").forEach(function(el) { el.remove(); });
            var container = document.getElementById("toast-container");
            if (container) { container.innerHTML = ""; }
            try {
                if (window.sessionStorage && tabUserId) {
                    var activeTabUid = window.sessionStorage.getItem("scripta_tab_uid");
                    var activeTabToken = window.sessionStorage.getItem("scripta_tab_token");
                    if (activeTabUid && activeTabToken && activeTabUid !== tabUserId) {
                        window.location.replace(anexarTokenNaUrl(window.location.href, activeTabToken));
                    }
                }
            } catch (err) {}
        }
    });

    // Previne envio duplo de formulários (evita mensagens de confirmação repetitivas e ações duplicadas)
    document.querySelectorAll("form").forEach(function(form) {
        form.addEventListener("submit", function() {
            var btnSubmit = form.querySelector("button[type='submit'], input[type='submit']");
            if (btnSubmit && !btnSubmit.disabled) {
                setTimeout(function() {
                    btnSubmit.disabled = true;
                }, 0);
            }
        });
    });

    // Previne que a tecla Backspace fora de campos editáveis cause navegação acidental para o login
    document.addEventListener("keydown", function(e) {
        if (e.key === "Backspace" || e.keyCode === 8) {
            var target = e.target;
            var tag = (target && target.tagName) ? target.tagName.toLowerCase() : "";
            var isEditable = tag === "input" || tag === "textarea" || (target && target.isContentEditable);
            if (!isEditable) {
                e.preventDefault();
            }
        }
    });
});
