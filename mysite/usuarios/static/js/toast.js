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
 * Converte elementos .msg vindos do Django no server-side em toasts
 * sem duplicidades, e previne cliques múltiplos acidentais.
 */
document.addEventListener("DOMContentLoaded", function() {
    var mensagensProcessadas = new Set();

    document.querySelectorAll(".msg").forEach(function(el) {
        var tipo = el.classList.contains("msg-success") ? "sucesso"
                 : el.classList.contains("msg-error") ? "erro"
                 : "aviso";
        var msg = (el.textContent || "").trim();
        if (msg && !mensagensProcessadas.has(msg)) {
            mensagensProcessadas.add(msg);

            // Deduplicação por chave de sessão para evitar repetições ao trocar de abas
            var chaveMsg = "toast_exibido_" + msg.replace(/\s+/g, "_").slice(0, 40);
            try {
                if (window.sessionStorage) {
                    var timestampAnterior = window.sessionStorage.getItem(chaveMsg);
                    if (timestampAnterior && (Date.now() - parseInt(timestampAnterior, 10) < 15000)) {
                        el.remove();
                        return;
                    }
                    window.sessionStorage.setItem(chaveMsg, Date.now().toString());
                }
            } catch (e) {}

            toast(msg, tipo, 4500);
        }
        // Remove do DOM para evitar reprocessamento
        el.remove();
    });

    // Se a página for restaurada do cache de navegação (bfcache), limpa toasts residuais
    window.addEventListener("pageshow", function(e) {
        if (e.persisted) {
            document.querySelectorAll(".msg").forEach(function(el) { el.remove(); });
            var container = document.getElementById("toast-container");
            if (container) { container.innerHTML = ""; }
        }
    });

    // Previne envio duplo de formulários (evita mensagens de confirmação repetitivas e ações duplicadas)
    document.querySelectorAll("form").forEach(function(form) {
        form.addEventListener("submit", function(e) {
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
