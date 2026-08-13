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
                    if(resposta.status===401){
                        return;
                    }
                    throw new Error("Erro na requisição");
                }

                const dados=await resposta.json();

                botao.querySelector("span").textContent=dados.curtidas;

                const icone=botao.querySelector(".icone-curtir");

                icone.src=dados.curtido
                    ?"/static/imgs/coracao-vermelho.png"
                    :"/static/imgs/coracao-cinza.png";

            }catch{

                alert("Erro ao curtir a publicação.");

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
