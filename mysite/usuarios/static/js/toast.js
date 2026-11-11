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
        setTimeout(removerToast, 400);
    }, duracao);
}

/**
 * Lightbox global seguro para ampliação de imagens (foto de perfil, banner, anexos e entregas).
 * Fecha com o botão "×", clicando em qualquer outro lugar fora da imagem, ou pressionando Esc.
 */
(function () {
    var backdrop = null;
    var imgEl = null;

    function criarModalSeNecessario() {
        if (backdrop) return;
        backdrop = document.createElement("div");
        backdrop.id = "global-lightbox-backdrop";
        backdrop.className = "lightbox-backdrop";
        backdrop.setAttribute("role", "dialog");
        backdrop.setAttribute("aria-modal", "true");
        backdrop.setAttribute("aria-hidden", "true");

        var btnFechar = document.createElement("button");
        btnFechar.type = "button";
        btnFechar.className = "lightbox-fechar";
        btnFechar.setAttribute("aria-label", "Fechar visualização");
        btnFechar.innerHTML = "&times;";

        imgEl = document.createElement("img");
        imgEl.className = "lightbox-img";
        imgEl.alt = "Visualização ampliada";

        btnFechar.addEventListener("click", function (e) {
            e.stopPropagation();
            fecharLightbox();
        });

        backdrop.addEventListener("click", function (e) {
            if (e.target !== imgEl) {
                fecharLightbox();
            }
        });

        backdrop.appendChild(btnFechar);
        backdrop.appendChild(imgEl);
        document.body.appendChild(backdrop);

        window.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && backdrop && backdrop.classList.contains("aberto")) {
                fecharLightbox();
            }
        });
    }

    function abrirLightbox(src, alt, circular) {
        if (!src) return;
        criarModalSeNecessario();
        imgEl.src = src;
        imgEl.alt = alt || "Imagem ampliada";
        imgEl.classList.toggle("lightbox-avatar-circular", !!circular);
        backdrop.classList.add("aberto");
        backdrop.setAttribute("aria-hidden", "false");
    }

    function fecharLightbox() {
        if (!backdrop) return;
        backdrop.classList.remove("aberto");
        backdrop.setAttribute("aria-hidden", "true");
    }

    window.abrirLightboxImagem = abrirLightbox;
    window.fecharLightboxImagem = fecharLightbox;
})();

// Remove eventuais resquícios de tokens antigos da barra de endereço (segurança)
(function limparParametroTokenDaUrl() {
    try {
        if (window.sessionStorage) {
            window.sessionStorage.removeItem("scripta_tab_uid");
            window.sessionStorage.removeItem("scripta_tab_token");
        }
        if (window.location.search && window.location.search.indexOf("_user_token") !== -1 && window.history && window.history.replaceState) {
            var params = new URLSearchParams(window.location.search);
            if (params.has("_user_token")) {
                params.delete("_user_token");
                var q = params.toString();
                var limpa = window.location.pathname + (q ? "?" + q : "") + window.location.hash;
                window.history.replaceState(null, "", limpa);
            }
        }
    } catch (e) {}
})();

document.addEventListener("DOMContentLoaded", function() {
    var userIdMeta = document.querySelector("meta[name='user-id']");
    var tabUserId = userIdMeta ? (userIdMeta.getAttribute("content") || "").trim() : "";

    // Abre qualquer imagem ampliável em lightbox ao clicar
    document.addEventListener("click", function (e) {
        var trigger = e.target && e.target.closest ? e.target.closest("[data-lightbox-src], .img-midia-anexada, .img-ampliavel") : null;
        if (!trigger) return;
        if (trigger.tagName && trigger.tagName.toLowerCase() === "a") {
            e.preventDefault();
        } else if (trigger.parentElement && trigger.parentElement.tagName && trigger.parentElement.tagName.toLowerCase() === "a" && !trigger.dataset.noInterceptLink) {
            e.preventDefault();
        }
        var src = trigger.getAttribute("data-lightbox-src") || trigger.getAttribute("src");
        var alt = trigger.getAttribute("data-lightbox-alt") || trigger.getAttribute("alt") || "Imagem";
        var circular = trigger.getAttribute("data-lightbox-circular") === "1";
        if (src && window.abrirLightboxImagem) {
            window.abrirLightboxImagem(src, alt, circular);
        }
    });

    // Verifica se a página foi aberta via botão Voltar/Avançar ou F5/Recarregar
    var ehNavegacaoHistoricoOuReload = false;
    try {
        if (window.performance) {
            if (typeof window.performance.getEntriesByType === "function") {
                var navEntries = window.performance.getEntriesByType("navigation");
                if (navEntries && navEntries.length > 0) {
                    var navType = navEntries[0].type;
                    if (navType === "back_forward" || navType === "reload") {
                        ehNavegacaoHistoricoOuReload = true;
                    }
                }
            } else if (window.performance.navigation) {
                var legacyType = window.performance.navigation.type;
                if (legacyType === 1 || legacyType === 2) {
                    ehNavegacaoHistoricoOuReload = true;
                }
            }
        }
    } catch (e) {}

    var mensagensProcessadas = new Set();

    document.querySelectorAll(".msg").forEach(function(el) {
        if (ehNavegacaoHistoricoOuReload) {
            el.remove();
            return;
        }
        var tipo = el.classList.contains("msg-success") ? "sucesso"
                 : el.classList.contains("msg-error") ? "erro"
                 : "aviso";
        var msg = (el.textContent || "").trim();
        var msgId = (el.getAttribute("data-msg-id") || "").trim();
        if (msg && !mensagensProcessadas.has(msg)) {
            mensagensProcessadas.add(msg);

            try {
                if (window.sessionStorage) {
                    if (msgId) {
                        var chaveIdUnico = "scripta_toast_id_" + msgId;
                        if (window.sessionStorage.getItem(chaveIdUnico)) {
                            el.remove();
                            return;
                        }
                        window.sessionStorage.setItem(chaveIdUnico, "1");
                    }

                    var chaveMsg = "toast_exibido_" + (tabUserId || "anon") + "_" + msg.replace(/\s+/g, "_").slice(0, 40);
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

    window.addEventListener("pageshow", function(e) {
        if (e.persisted) {
            document.querySelectorAll(".msg").forEach(function(el) { el.remove(); });
            var container = document.getElementById("toast-container");
            if (container) { container.innerHTML = ""; }
        }
    });

    // Previne envio duplo de formulários
    document.querySelectorAll("form").forEach(function(form) {
        form.addEventListener("submit", function(e) {
            if (e && e.defaultPrevented) return;
            var btnSubmit = form.querySelector("button[type='submit'], input[type='submit']");
            if (btnSubmit && !btnSubmit.disabled) {
                setTimeout(function() {
                    if (e && e.defaultPrevented) return;
                    btnSubmit.disabled = true;
                }, 0);
            }
        });
    });

    // Previne que Backspace fora de campos editáveis navegue de volta acidentalmente
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
