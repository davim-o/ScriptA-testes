const abrirDiretoria = document.getElementById("abrirDiretoria");
const listaDiretoria = document.getElementById("listaDiretoria");
const setaDiretoria = document.getElementById("setaDiretoria");
const textoDiretoria = document.getElementById("textoDiretoria");

const abrirAreas = document.getElementById("abrirAreas");
const listaAreas = document.getElementById("listaAreas");
const setaAreas = document.getElementById("setaAreas");

const opcoesDiretoria = document.querySelectorAll(".opcao-diretoria");


abrirDiretoria.addEventListener("click", () => {
    const ativo = listaDiretoria.classList.toggle("ativo");

    setaDiretoria.src = ativo ? SETA_CIMA : SETA_BAIXO;
});

opcoesDiretoria.forEach(opcao => {
    opcao.addEventListener("click", () => {
        textoDiretoria.textContent = opcao.textContent;
        document.getElementById("diretoriaSelecionada").value = opcao.textContent;

        listaDiretoria.classList.remove("ativo");
        setaDiretoria.src = SETA_BAIXO;
    });
});


abrirAreas.addEventListener("click", () => {
    const ativo = listaAreas.classList.toggle("ativo");

    setaAreas.src = ativo ? SETA_CIMA : SETA_BAIXO;
});


document.addEventListener("click", (evento) => {

    if (!abrirDiretoria.contains(evento.target) && !listaDiretoria.contains(evento.target)) {
        listaDiretoria.classList.remove("ativo");
        setaDiretoria.src = SETA_BAIXO;
    }

    if (!abrirAreas.contains(evento.target) && !listaAreas.contains(evento.target)) {
        listaAreas.classList.remove("ativo");
        setaAreas.src = SETA_BAIXO;
    }
});