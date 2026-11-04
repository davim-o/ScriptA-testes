document.addEventListener("DOMContentLoaded", function () {
    // 1. Curtir mensagem do chat da área
    document.querySelectorAll(".btn-curtir-chat").forEach(function (botao) {
        var processando = false;

        botao.addEventListener("click", async function () {
            if (processando) return;
            processando = true;
            botao.disabled = true;

            var id = botao.dataset.id;

            try {
                var resposta = await fetch("/area/chat/curtir/" + id + "/", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": getCookieChat("csrftoken"),
                        "X-Requested-With": "XMLHttpRequest",
                    },
                });

                if (!resposta.ok) {
                    var msgErro = "Não foi possível curtir a mensagem.";
                    try {
                        var erroJson = await resposta.json();
                        if (erroJson && erroJson.erro) msgErro = erroJson.erro;
                    } catch (_) {}
                    if (typeof toast === "function") {
                        toast(msgErro, "erro");
                    }
                    return;
                }

                var dados = await resposta.json();
                var spanContador = botao.querySelector(".contador-curtidas-chat");
                if (spanContador) {
                    spanContador.textContent = dados.curtidas;
                }

                var icone = botao.querySelector(".icone-curtir-chat");
                if (icone) {
                    icone.src = dados.curtido
                        ? "/static/imgs/coracao-vermelho.png"
                        : "/static/imgs/coracao-cinza.png";
                }
                botao.classList.toggle("curtido", !!dados.curtido);
            } catch (err) {
                if (typeof toast === "function") {
                    toast("Erro ao curtir a mensagem.", "erro");
                }
            } finally {
                processando = false;
                botao.disabled = false;
            }
        });
    });

    // 2. Responder a uma mensagem do chat da área
    var inputRespostaA = document.getElementById("input-resposta-a");
    var previewBox = document.getElementById("preview-resposta-chat");
    var previewAvatar = document.getElementById("preview-resposta-avatar");
    var previewAutor = document.getElementById("preview-resposta-autor");
    var previewTexto = document.getElementById("preview-resposta-texto");
    var btnCancelarResposta = document.getElementById("btn-cancelar-resposta");
    var textareaChat = document.getElementById("textarea-chat-area");
    var boxNovaMensagem = document.getElementById("box-nova-mensagem");
    var placeholderPadrao = textareaChat ? textareaChat.getAttribute("placeholder") : "";

    document.querySelectorAll(".btn-responder-chat").forEach(function (botao) {
        botao.addEventListener("click", function () {
            var id = botao.dataset.id || "";
            var autor = botao.dataset.autor || "";
            var inicial = botao.dataset.inicial || "U";
            var foto = botao.dataset.foto || "";
            var cor = botao.dataset.cor || "avatar-chat-roxo";
            var texto = botao.dataset.texto || "";

            if (inputRespostaA) {
                inputRespostaA.value = id;
            }
            if (previewAutor) {
                previewAutor.textContent = autor;
            }
            if (previewTexto) {
                previewTexto.textContent = texto;
            }
            if (previewAvatar) {
                previewAvatar.className = "chat-avatar chat-avatar-pequeno " + cor;
                if (foto) {
                    previewAvatar.innerHTML = "";
                    var imgEl = document.createElement("img");
                    imgEl.src = foto;
                    imgEl.alt = autor;
                    imgEl.className = "avatar-foto-img";
                    previewAvatar.appendChild(imgEl);
                } else {
                    previewAvatar.textContent = inicial;
                }
            }
            if (previewBox) {
                previewBox.style.display = "flex";
            }
            if (boxNovaMensagem && boxNovaMensagem.scrollIntoView) {
                boxNovaMensagem.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            if (textareaChat) {
                textareaChat.placeholder = "Respondendo a " + autor + "...";
                textareaChat.focus();
            }
        });
    });

    if (btnCancelarResposta) {
        btnCancelarResposta.addEventListener("click", function () {
            if (inputRespostaA) {
                inputRespostaA.value = "";
            }
            if (previewBox) {
                previewBox.style.display = "none";
            }
            if (textareaChat) {
                textareaChat.placeholder = placeholderPadrao;
            }
        });
    }

    // 3. Confirmação ao excluir mensagem
    document.querySelectorAll(".form-excluir-chat").forEach(function (form) {
        form.addEventListener("submit", function (e) {
            if (!confirm("Deseja excluir esta mensagem?")) {
                e.preventDefault();
            }
        });
    });
});

function getCookieChat(nome) {
    var valor = null;
    if (!document.cookie) return valor;
    document.cookie.split(";").forEach(function (cookie) {
        cookie = cookie.trim();
        if (cookie.indexOf(nome + "=") === 0) {
            valor = decodeURIComponent(cookie.substring(nome.length + 1));
        }
    });
    return valor;
}

