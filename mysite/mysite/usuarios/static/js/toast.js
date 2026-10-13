/**
 * toast(mensagem, tipo, duração_ms)
 * tipo: "erro" | "sucesso" | "aviso"   (padrão: "erro")
 * Cria um container fixo no topo e empilha toasts.
 * Cada toast some sozinho após `duracao` ms.
 * Garante que mensagens idênticas nunca apareçam simultaneamente.
 */
var mensagensAtivas = new Set();

function toast(mensagem, tipo, duracao) {
    if (!mensagem || typeof mensagem !== "string") return;
    mensagem = mensagem.trim();
    if (!mensagem) return;

    // Deduplicação: se a mesma mensagem já está em exibição, não cria outra
    if (mensagensAtivas.has(mensagem)) {
        return;
    }
    mensagensAtivas.add(mensagem);

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
            toast(msg, tipo, 4500);
        }
        // Remove do DOM para evitar reprocessamento
        el.remove();
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
