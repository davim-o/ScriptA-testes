(function () {
    "use strict";

    function aplicarFormatacao(campo, prefixo, sufixo, placeholder) {
        campo.focus();
        var inicio = campo.selectionStart || 0;
        var fim = campo.selectionEnd || 0;
        var valor = campo.value || "";
        var selecionado = valor.substring(inicio, fim);
        var textoInserir = selecionado || placeholder || "texto";
        var novoTexto =
            valor.substring(0, inicio) +
            prefixo +
            textoInserir +
            sufixo +
            valor.substring(fim);

        if (campo.maxLength && campo.maxLength > 0 && novoTexto.length > campo.maxLength) {
            return;
        }

        campo.value = novoTexto;
        var novoInicio = inicio + prefixo.length;
        var novoFim = novoInicio + textoInserir.length;
        campo.setSelectionRange(novoInicio, novoFim);
        campo.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function aplicarPrefixoLinha(campo, prefixo) {
        campo.focus();
        var inicio = campo.selectionStart || 0;
        var fim = campo.selectionEnd || 0;
        var valor = campo.value || "";
        var inicioLinha = valor.lastIndexOf("\n", Math.max(0, inicio - 1)) + 1;
        var trecho = valor.substring(inicioLinha, fim);
        var linhas = trecho ? trecho.split("\n") : [""];
        var formatadas = linhas.map(function (l) {
            if (l.startsWith(prefixo)) {
                return l.substring(prefixo.length);
            }
            return prefixo + l;
        });
        var blocoNovo = formatadas.join("\n");
        var novoTexto = valor.substring(0, inicioLinha) + blocoNovo + valor.substring(fim);
        if (campo.maxLength && campo.maxLength > 0 && novoTexto.length > campo.maxLength) {
            return;
        }
        campo.value = novoTexto;
        campo.setSelectionRange(inicioLinha, inicioLinha + blocoNovo.length);
        campo.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function limparFormatacaoTrecho(campo) {
        campo.focus();
        var inicio = campo.selectionStart || 0;
        var fim = campo.selectionEnd || 0;
        var valor = campo.value || "";
        if (inicio === fim) return;
        var selecionado = valor.substring(inicio, fim);
        var limpo = selecionado
            .replace(/\*\*([^*]+)\*\*/g, "$1")
            .replace(/__([^_]+)__/g, "$1")
            .replace(/~~([^~]+)~~/g, "$1")
            .replace(/\*([^*]+)\*/g, "$1")
            .replace(/`([^`]+)`/g, "$1")
            .replace(/^[>•\-]\s+/gm, "");
        campo.value = valor.substring(0, inicio) + limpo + valor.substring(fim);
        campo.setSelectionRange(inicio, inicio + limpo.length);
        campo.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function inicializarBarra(campo) {
        if (!campo || campo.dataset.rtInitialized === "1") return;
        campo.dataset.rtInitialized = "1";

        var barra = document.createElement("div");
        barra.className = "rt-toolbar";
        barra.setAttribute("role", "toolbar");
        barra.setAttribute("aria-label", "Ferramentas de formatação de texto");

        var botoes = [
            { label: "B", title: "Negrito (Ctrl+B)", cls: "rt-btn-bold", acao: function () { aplicarFormatacao(campo, "**", "**", "negrito"); } },
            { label: "I", title: "Itálico (Ctrl+I)", cls: "rt-btn-italic", acao: function () { aplicarFormatacao(campo, "*", "*", "itálico"); } },
            { label: "U", title: "Sublinhado (Ctrl+U)", cls: "rt-btn-underline", acao: function () { aplicarFormatacao(campo, "__", "__", "sublinhado"); } },
            { label: "S", title: "Tachado", cls: "rt-btn-strike", acao: function () { aplicarFormatacao(campo, "~~", "~~", "tachado"); } },
            { label: "• Lista", title: "Lista com marcadores", cls: "rt-btn-list", acao: function () { aplicarPrefixoLinha(campo, "• "); } },
            { label: "❝ Citação", title: "Bloco de citação", cls: "rt-btn-quote", acao: function () { aplicarPrefixoLinha(campo, "> "); } },
            { label: "Limpar", title: "Remover formatação do texto selecionado", cls: "rt-btn-clear", acao: function () { limparFormatacaoTrecho(campo); } }
        ];

        var grupoBtns = document.createElement("div");
        grupoBtns.className = "rt-toolbar-group";

        botoes.forEach(function (cfg) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "rt-btn " + cfg.cls;
            btn.title = cfg.title;
            btn.textContent = cfg.label;
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                cfg.acao();
            });
            grupoBtns.appendChild(btn);
        });

        barra.appendChild(grupoBtns);

        var maxLen = parseInt(campo.getAttribute("maxlength") || "0", 10);
        var contador = null;
        if (maxLen > 0 && !campo.dataset.hideRtCounter) {
            contador = document.createElement("span");
            contador.className = "rt-char-counter";
            barra.appendChild(contador);
            var atualizarContador = function () {
                var atual = (campo.value || "").length;
                contador.textContent = atual + "/" + maxLen;
                contador.classList.toggle("rt-counter-limit", atual >= maxLen * 0.92);
            };
            campo.addEventListener("input", atualizarContador);
            atualizarContador();
        }

        campo.addEventListener("keydown", function (e) {
            if (e.ctrlKey || e.metaKey) {
                var k = (e.key || "").toLowerCase();
                if (k === "b") {
                    e.preventDefault();
                    aplicarFormatacao(campo, "**", "**", "negrito");
                } else if (k === "i") {
                    e.preventDefault();
                    aplicarFormatacao(campo, "*", "*", "itálico");
                } else if (k === "u") {
                    e.preventDefault();
                    aplicarFormatacao(campo, "__", "__", "sublinhado");
                }
            }
        });

        var containerAlvo = campo.closest(".rt-editor-box");
        if (containerAlvo) {
            containerAlvo.insertBefore(barra, containerAlvo.firstChild);
        } else if (campo.parentNode) {
            var wrapper = document.createElement("div");
            wrapper.className = "rt-editor-wrap";
            campo.parentNode.insertBefore(wrapper, campo);
            wrapper.appendChild(barra);
            wrapper.appendChild(campo);
        }
    }

    function inicializarTodos() {
        document.querySelectorAll("[data-rich-editor]").forEach(inicializarBarra);

        document.querySelectorAll("[data-toggle-edit]").forEach(function (btn) {
            if (btn.dataset.boundEdit === "1") return;
            btn.dataset.boundEdit = "1";
            btn.addEventListener("click", function () {
                var targetId = btn.getAttribute("data-toggle-edit");
                var box = document.getElementById(targetId);
                if (!box) return;
                var oculto = box.style.display === "none" || !box.style.display;
                box.style.display = oculto ? "block" : "none";
                if (oculto) {
                    var campo = box.querySelector("textarea, input[type='text']");
                    if (campo) {
                        inicializarBarra(campo);
                        campo.focus();
                        var tam = (campo.value || "").length;
                        try { campo.setSelectionRange(tam, tam); } catch (_) {}
                    }
                }
            });
        });

        document.querySelectorAll("[data-cancel-edit]").forEach(function (btn) {
            if (btn.dataset.boundCancel === "1") return;
            btn.dataset.boundCancel = "1";
            btn.addEventListener("click", function () {
                var targetId = btn.getAttribute("data-cancel-edit");
                var box = document.getElementById(targetId);
                if (box) box.style.display = "none";
            });
        });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", inicializarTodos);
    } else {
        inicializarTodos();
    }
    window.inicializarEditoresTexto = inicializarTodos;
})();
