document.addEventListener("DOMContentLoaded",()=>{

    document.querySelectorAll(".curtir").forEach(botao=>{

        let processando=false;

        botao.addEventListener("click",async()=>{

            if(processando) return;
            processando=true;
            botao.disabled=true;

            const id=botao.dataset.id;

            try{

                const resposta=await fetch(`/curtir/${id}/`,{
                    method:"POST",
                    headers:{
                        "X-CSRFToken":getCookie("csrftoken"),
                        "X-Requested-With":"XMLHttpRequest"
                    }
                });

                if(!resposta.ok){
                    let msgErro="Não foi possível curtir a publicação.";
                    try{
                        const erroJson=await resposta.json();
                        if(erroJson && erroJson.erro) msgErro=erroJson.erro;
                    }catch(_){}
                    if(typeof toast==="function"){
                        toast(msgErro,"erro");
                    }
                    return;
                }

                const dados=await resposta.json();

                botao.querySelector("span").textContent=dados.curtidas;

                const icone=botao.querySelector(".icone-curtir");

                icone.src=dados.curtido
                    ?"/static/imgs/coracao-vermelho.png"
                    :"/static/imgs/coracao-cinza.png";

            }catch(err){
                if(typeof toast==="function"){
                    toast("Falha de conexão ao curtir a publicação. Tente novamente.","erro");
                }
            }finally{

                processando=false;
                botao.disabled=false;

            }

        });

    });

    document.querySelectorAll(".form-excluir").forEach(form=>{

        form.addEventListener("submit",e=>{

            if(!confirm("Deseja excluir esta publicação?")){

                e.preventDefault();

            }

        });

    });

    // Responder publicação no Feed
    const inputRespostaFeed = document.getElementById("input-resposta-feed");
    const previewRespBox = document.getElementById("preview-resposta-feed");
    const previewRespAvatar = document.getElementById("preview-resposta-feed-avatar");
    const previewRespAutor = document.getElementById("preview-resposta-feed-autor");
    const previewRespTexto = document.getElementById("preview-resposta-feed-texto");
    const btnCancelarRespFeed = document.getElementById("btn-cancelar-resposta-feed");
    const textareaFeed = document.getElementById("textarea-feed");
    const boxNovaPub = document.getElementById("box-nova-publicacao-feed");
    const placeholderOriginalFeed = textareaFeed ? textareaFeed.getAttribute("placeholder") : "";

    document.querySelectorAll(".btn-responder-feed").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.dataset.id || "";
            const autor = btn.dataset.autor || "";
            const inicial = btn.dataset.inicial || "U";
            const foto = btn.dataset.foto || "";
            const texto = btn.dataset.texto || "";

            if (inputRespostaFeed) inputRespostaFeed.value = id;
            if (previewRespAutor) previewRespAutor.textContent = "Respondendo a " + autor;
            if (previewRespTexto) previewRespTexto.textContent = texto;
            if (previewRespAvatar) {
                previewRespAvatar.textContent = "";
                if (foto) {
                    const imgEl = document.createElement("img");
                    imgEl.src = foto;
                    imgEl.alt = autor;
                    imgEl.className = "avatar-foto-img";
                    previewRespAvatar.appendChild(imgEl);
                } else {
                    previewRespAvatar.textContent = inicial;
                }
            }
            if (previewRespBox) previewRespBox.style.display = "flex";
            if (boxNovaPub && boxNovaPub.scrollIntoView) {
                boxNovaPub.scrollIntoView({ behavior: "smooth", block: "nearest" });
            }
            if (textareaFeed) {
                textareaFeed.placeholder = "Respondendo a " + autor + "...";
                textareaFeed.focus();
            }
        });
    });

    if (btnCancelarRespFeed) {
        btnCancelarRespFeed.addEventListener("click", () => {
            if (inputRespostaFeed) inputRespostaFeed.value = "";
            if (previewRespBox) previewRespBox.style.display = "none";
            if (textareaFeed) textareaFeed.placeholder = placeholderOriginalFeed;
        });
    }

    // Preview de imagem anexada no Feed e validação texto-ou-imagem
    const inputImgFeed = document.getElementById("input-img-feed");
    const previewAnexoBox = document.getElementById("preview-anexo-feed");
    const imgPreviewFeed = document.getElementById("img-preview-feed");
    const nomePreviewFeed = document.getElementById("nome-preview-feed");
    const btnRemoverAnexoFeed = document.getElementById("btn-remover-anexo-feed");
    const formPublicarFeed = document.getElementById("form-publicar-feed");
    let objectUrlFeed = null;

    function limparAnexoFeed() {
        if (inputImgFeed) inputImgFeed.value = "";
        if (previewAnexoBox) previewAnexoBox.classList.remove("ativo");
        if (imgPreviewFeed) imgPreviewFeed.removeAttribute("src");
        if (nomePreviewFeed) nomePreviewFeed.textContent = "";
        if (objectUrlFeed) {
            URL.revokeObjectURL(objectUrlFeed);
            objectUrlFeed = null;
        }
    }

    if (inputImgFeed) {
        inputImgFeed.addEventListener("change", () => {
            const file = inputImgFeed.files && inputImgFeed.files[0];
            if (!file) {
                limparAnexoFeed();
                return;
            }
            if (objectUrlFeed) URL.revokeObjectURL(objectUrlFeed);
            objectUrlFeed = URL.createObjectURL(file);
            if (imgPreviewFeed) imgPreviewFeed.src = objectUrlFeed;
            if (nomePreviewFeed) nomePreviewFeed.textContent = file.name;
            if (previewAnexoBox) previewAnexoBox.classList.add("ativo");
        });
    }

    if (btnRemoverAnexoFeed) {
        btnRemoverAnexoFeed.addEventListener("click", limparAnexoFeed);
    }

    if (formPublicarFeed) {
        formPublicarFeed.addEventListener("submit", e => {
            const temTexto = textareaFeed && textareaFeed.value.trim().length > 0;
            const temImg = inputImgFeed && inputImgFeed.files && inputImgFeed.files.length > 0;
            if (!temTexto && !temImg) {
                e.preventDefault();
                if (typeof toast === "function") {
                    toast("Escreva uma mensagem ou selecione uma imagem para publicar.", "erro");
                }
            }
        });
    }

    // Ir até publicação citada / resposta recente com flash
    document.querySelectorAll("[data-scroll-to]").forEach(trigger => {
        trigger.addEventListener("click", e => {
            if (e.target.closest("a")) return;
            const targetId = trigger.getAttribute("data-scroll-to");
            const alvo = targetId ? document.getElementById(targetId) : null;
            if (!alvo) return;
            alvo.scrollIntoView({ behavior: "smooth", block: "center" });
            alvo.classList.remove("card-flash-destaque");
            void alvo.offsetWidth;
            alvo.classList.add("card-flash-destaque");
        });
    });

});

function getCookie(nome){

    let valor=null;

    document.cookie.split(";").forEach(cookie=>{

        cookie=cookie.trim();

        if(cookie.startsWith(nome+"="))

            valor=decodeURIComponent(cookie.substring(nome.length+1));

    });

    return valor;

}
