/**
 * toast(mensagem, tipo, duração_ms)
 * tipo: "erro" | "sucesso" | "aviso"   (padrão: "erro")
 * Cria um container fixo no topo e empilha toasts.
 * Cada toast some sozinho após `duracao` ms.
 */
function toast(mensagem, tipo, duracao) {
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

    setTimeout(function() {
        el.classList.add("saindo");
        el.addEventListener("animationend", function() { el.remove(); }, { once: true });
    }, duracao);
}

/**
 * Converte todos os elementos .erro-login existentes no HTML
 * (vindos do Django no server-side) em toasts, para manter
 * a mesma estética sem alterar cada template manualmente.
 */
document.addEventListener("DOMContentLoaded", function() {
    document.querySelectorAll(".msg").forEach(function(el) {
        var tipo = el.classList.contains("msg-success") ? "sucesso"
                 : el.classList.contains("msg-error") ? "erro"
                 : "aviso";
        var msg = el.textContent.trim();
        if (msg) toast(msg, tipo, 5000);
        el.style.display = "none";
    });
});
