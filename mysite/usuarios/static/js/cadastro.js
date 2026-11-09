const inputDiretoria = document.getElementById("diretoriaSelecionada");
const abrirAreas = document.getElementById("abrirAreas");
const listaAreas = document.getElementById("listaAreas");
const setaAreas = document.getElementById("setaAreas");
const textoAreasSelecionadas = document.getElementById("textoAreasSelecionadas");

const inputMatriculaCadastro = document.getElementById("matricula-cadastro");
const inputSenhaCadastro = document.getElementById("senha");

const CODIGOS_DIRETORIA_MATRICULA = {
    "01111": "Diatinf", "1111": "Diatinf", "01140": "Diatinf", "1140": "Diatinf",
    "01112": "Diatinf", "1112": "Diatinf", "01141": "Diatinf",
    "01113": "Diatinf", "1113": "Diatinf", "01142": "Diatinf",
    "01159": "Diatinf", "0159": "Diatinf", "01160": "Diatinf", "0160": "Diatinf",
    "01101": "Diaren",  "1101": "Diaren",  "0101": "Diaren",
    "01102": "Diaren",  "1102": "Diaren",  "0102": "Diaren",
    "01103": "Diaren",  "1103": "Diaren",  "0103": "Diaren",
    "01151": "Diaren",  "0151": "Diaren",
    "01201": "Diacon",  "1201": "Diacon",  "01121": "Diacon", "0201": "Diacon",
    "01202": "Diacon",  "1202": "Diacon",  "01122": "Diacon", "0202": "Diacon",
    "01152": "Diacon",  "0152": "Diacon",
    "01301": "Diacin",  "1301": "Diacin",  "01131": "Diacin", "0301": "Diacin",
    "01302": "Diacin",  "1302": "Diacin",  "01132": "Diacin", "0302": "Diacin",
    "01303": "Diacin",  "1303": "Diacin",  "01133": "Diacin", "0303": "Diacin",
    "01304": "Diacin",  "1304": "Diacin",  "01134": "Diacin", "0304": "Diacin"
};

let timerConsultaSuap = null;

function identificarDiretoriaLocal(matricula) {
    const mat = (matricula || "").trim();
    if (!/^\d+$/.test(mat) || mat.length < 10) return "";
    const meio = mat.length >= 11 ? mat.slice(5, -4) : mat.slice(4, -4);
    const candidatos = [meio, mat.slice(5, 10), mat.slice(5, 9), mat.slice(4, 9), mat.slice(4, 8)];
    for (let i = 0; i < candidatos.length; i++) {
        const cod = candidatos[i];
        if (CODIGOS_DIRETORIA_MATRICULA[cod]) {
            return CODIGOS_DIRETORIA_MATRICULA[cod];
        }
    }
    return "";
}

function definirDiretoriaNoFormulario(diretoria) {
    if (!inputDiretoria) return;
    inputDiretoria.value = diretoria || "";
}

function consultarSuapAutomatico(incluirSenha) {
    if (!inputMatriculaCadastro) return;
    const mat = (inputMatriculaCadastro.value || "").trim();
    if (mat.length < 6) {
        definirDiretoriaNoFormulario("");
        return;
    }

    const dirLocal = identificarDiretoriaLocal(mat);
    if (dirLocal) {
        definirDiretoriaNoFormulario(dirLocal);
    }

    const params = new URLSearchParams();
    params.set("matricula", mat);
    if (incluirSenha && inputSenhaCadastro && inputSenhaCadastro.value) {
        params.set("senha", inputSenhaCadastro.value);
    }

    fetch("/api/suap/verificar/?" + params.toString(), {
        method: "GET",
        headers: { "Accept": "application/json" }
    })
        .then(r => r.json())
        .then(dados => {
            if (dados && dados.diretoria) {
                definirDiretoriaNoFormulario(dados.diretoria);
            } else if (!dirLocal) {
                definirDiretoriaNoFormulario("");
            }
        })
        .catch(() => {});
}

if (inputMatriculaCadastro) {
    inputMatriculaCadastro.addEventListener("input", () => {
        const mat = (inputMatriculaCadastro.value || "").trim();
        const dirLocal = identificarDiretoriaLocal(mat);
        if (dirLocal) {
            definirDiretoriaNoFormulario(dirLocal);
        } else if (mat.length < 6) {
            definirDiretoriaNoFormulario("");
        }
        clearTimeout(timerConsultaSuap);
        timerConsultaSuap = setTimeout(() => consultarSuapAutomatico(false), 220);
    });
    inputMatriculaCadastro.addEventListener("blur", () => {
        consultarSuapAutomatico(true);
    });
}

if (inputSenhaCadastro) {
    inputSenhaCadastro.addEventListener("blur", () => {
        if (inputMatriculaCadastro && inputMatriculaCadastro.value.trim().length >= 6) {
            consultarSuapAutomatico(true);
        }
    });
}

if (abrirAreas && listaAreas) {
    abrirAreas.addEventListener("click", () => {
        const ativo = listaAreas.classList.toggle("ativo");
        if (setaAreas) {
            setaAreas.src = ativo ? SETA_CIMA : SETA_BAIXO;
        }
    });
}

function atualizarTextoAreas() {
    if (!listaAreas || !textoAreasSelecionadas) return;
    const marcadas = Array.from(listaAreas.querySelectorAll('input[type="checkbox"]:checked')).map(cb => cb.value);
    if (marcadas.length > 0) {
        textoAreasSelecionadas.textContent = marcadas.join(", ");
        textoAreasSelecionadas.classList.remove("placeholder-ghost");
    } else {
        textoAreasSelecionadas.textContent = "Selecione as áreas (opcional)";
        textoAreasSelecionadas.classList.add("placeholder-ghost");
    }
}

if (listaAreas) {
    listaAreas.addEventListener("change", atualizarTextoAreas);
    atualizarTextoAreas();
}

document.addEventListener("click", (evento) => {
    if (abrirAreas && listaAreas && !abrirAreas.contains(evento.target) && !listaAreas.contains(evento.target)) {
        listaAreas.classList.remove("ativo");
        if (setaAreas) setaAreas.src = SETA_BAIXO;
    }
});

const toggleSenhaCadastro = document.getElementById("toggle-senha-cadastro");
if (toggleSenhaCadastro && inputSenhaCadastro) {
    toggleSenhaCadastro.addEventListener("click", () => {
        const mostrar = inputSenhaCadastro.type === "password";
        inputSenhaCadastro.type = mostrar ? "text" : "password";
        const aberto = toggleSenhaCadastro.querySelector(".icone-olho-aberto");
        const fechado = toggleSenhaCadastro.querySelector(".icone-olho-fechado");
        if (aberto && fechado) {
            aberto.style.display = mostrar ? "none" : "block";
            fechado.style.display = mostrar ? "block" : "none";
        }
        toggleSenhaCadastro.setAttribute("aria-label", mostrar ? "Ocultar senha" : "Mostrar senha");
        if (window.definirOlhosMascotesFechados) {
            window.definirOlhosMascotesFechados(mostrar);
        }
    });
}
