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

    // 4. Preview de imagem anexada no Chat de Área e validação texto-ou-imagem
    var inputImgChat = document.getElementById("input-img-chat");
    var previewAnexoChat = document.getElementById("preview-anexo-chat");
    var imgPreviewChat = document.getElementById("img-preview-chat");
    var nomePreviewChat = document.getElementById("nome-preview-chat");
    var btnRemoverAnexoChat = document.getElementById("btn-remover-anexo-chat");
    var formChatArea = document.getElementById("form-chat-area");
    var objectUrlChat = null;

    function limparAnexoChat() {
        if (inputImgChat) inputImgChat.value = "";
        if (previewAnexoChat) previewAnexoChat.classList.remove("ativo");
        if (imgPreviewChat) imgPreviewChat.removeAttribute("src");
        if (nomePreviewChat) nomePreviewChat.textContent = "";
        if (objectUrlChat) {
            URL.revokeObjectURL(objectUrlChat);
            objectUrlChat = null;
        }
    }

    if (inputImgChat) {
        inputImgChat.addEventListener("change", function () {
            var file = inputImgChat.files && inputImgChat.files[0];
            if (!file) {
                limparAnexoChat();
                return;
            }
            if (objectUrlChat) URL.revokeObjectURL(objectUrlChat);
            objectUrlChat = URL.createObjectURL(file);
            if (imgPreviewChat) imgPreviewChat.src = objectUrlChat;
            if (nomePreviewChat) nomePreviewChat.textContent = file.name;
            if (previewAnexoChat) previewAnexoChat.classList.add("ativo");
        });
    }

    if (btnRemoverAnexoChat) {
        btnRemoverAnexoChat.addEventListener("click", limparAnexoChat);
    }

    if (formChatArea) {
        formChatArea.addEventListener("submit", function (e) {
            var temTexto = textareaChat && textareaChat.value.trim().length > 0;
            var temImg = inputImgChat && inputImgChat.files && inputImgChat.files.length > 0;
            if (!temTexto && !temImg) {
                e.preventDefault();
                if (typeof toast === "function") {
                    toast("Escreva uma mensagem ou selecione uma imagem para enviar.", "erro");
                }
            }
        });
    }

    // 5. Ir até mensagem citada / resposta recente com flash
    document.querySelectorAll("[data-scroll-to]").forEach(function (trigger) {
        trigger.addEventListener("click", function (e) {
            if (e.target.closest("a")) return;
            var targetId = trigger.getAttribute("data-scroll-to");
            var alvo = targetId ? document.getElementById(targetId) : null;
            if (!alvo) return;
            alvo.scrollIntoView({ behavior: "smooth", block: "center" });
            alvo.classList.remove("chat-card-flash-destaque");
            void alvo.offsetWidth;
            alvo.classList.add("chat-card-flash-destaque");
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
