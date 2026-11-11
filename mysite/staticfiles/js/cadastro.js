const inputDiretoria = document.getElementById("diretoriaSelecionada");
const selectDiretoriaManual = document.getElementById("diretoriaManualSelect");
const formCadastro = document.getElementById("form-cadastro");
const abrirAreas = document.getElementById("abrirAreas");
const listaAreas = document.getElementById("listaAreas");
const setaAreas = document.getElementById("setaAreas");
const textoAreasSelecionadas = document.getElementById("textoAreasSelecionadas");

const inputMatriculaCadastro = document.getElementById("matricula-cadastro");
const inputSenhaCadastro = document.getElementById("senha");
const suapStatusMsg = document.getElementById("suapStatusMsg");
const cursoSuapExibicao = document.getElementById("cursoSuapExibicao");

const hiddenSuapVerificado = document.getElementById("suapVerificadoCliente");
const hiddenSuapNome = document.getElementById("suapNomeCliente");
const hiddenSuapCurso = document.getElementById("suapCursoCliente");
const hiddenSuapDiretoria = document.getElementById("suapDiretoriaCliente");
const hiddenSuapExtras = document.getElementById("suapExtrasCliente");

// Apenas códigos confirmados para pré-preenchimento local antes da resposta da API
const CODIGOS_DIRETORIA_MATRICULA = {
    "01111": "Diatinf",
    "01404": "Diatinf"
};

let timerConsultaSuap = null;
let autenticacaoSuapValidada = false;
let credenciaisSuapInvalidas = false;
let ultimaChaveConsultada = "";
let verificacaoEmCursoPromise = null;

function obterCsrfCadastro() {
    const inp = document.querySelector('#form-cadastro input[name="csrfmiddlewaretoken"]');
    if (inp && inp.value) return inp.value;
    let valor = "";
    if (document.cookie) {
        document.cookie.split(";").forEach(cookie => {
            cookie = cookie.trim();
            if (cookie.startsWith("csrftoken=")) {
                valor = decodeURIComponent(cookie.substring("csrftoken=".length));
            }
        });
    }
    return valor;
}

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

function limparCamposClienteSuap() {
    if (hiddenSuapVerificado) hiddenSuapVerificado.value = "0";
    if (hiddenSuapNome) hiddenSuapNome.value = "";
    if (hiddenSuapCurso) hiddenSuapCurso.value = "";
    if (hiddenSuapDiretoria) hiddenSuapDiretoria.value = "";
    if (hiddenSuapExtras) hiddenSuapExtras.value = "";
}

function preencherCamposClienteSuap(dadosCli) {
    if (hiddenSuapVerificado) hiddenSuapVerificado.value = dadosCli.verificado ? "1" : "0";
    if (hiddenSuapNome) hiddenSuapNome.value = (dadosCli.nome || "").slice(0, 100);
    if (hiddenSuapCurso) hiddenSuapCurso.value = (dadosCli.curso || "").slice(0, 200);
    if (hiddenSuapDiretoria) hiddenSuapDiretoria.value = (dadosCli.diretoria || "").slice(0, 100);
    if (hiddenSuapExtras) hiddenSuapExtras.value = (dadosCli.extras || "").slice(0, 1000);
}

function alternarModoEscolhaDiretoria(permitirManual) {
    if (!inputDiretoria || !selectDiretoriaManual) return;
    if (permitirManual) {
        inputDiretoria.style.display = "none";
        selectDiretoriaManual.style.display = "block";
        if (inputDiretoria.value) {
            selectDiretoriaManual.value = inputDiretoria.value;
        }
    } else {
        selectDiretoriaManual.style.display = "none";
        inputDiretoria.style.display = "block";
    }
}

function definirDiretoriaNoFormulario(diretoria, curso, permitirManual) {
    if (permitirManual) {
        alternarModoEscolhaDiretoria(true);
        if (diretoria && selectDiretoriaManual) {
            selectDiretoriaManual.value = diretoria;
        }
        if (inputDiretoria && selectDiretoriaManual) {
            inputDiretoria.value = selectDiretoriaManual.value || diretoria || "";
        }
    } else {
        alternarModoEscolhaDiretoria(false);
        if (inputDiretoria) {
            inputDiretoria.value = diretoria || "";
        }
    }
    if (cursoSuapExibicao) {
        if (curso) {
            cursoSuapExibicao.textContent = "Curso: " + curso;
            cursoSuapExibicao.style.display = "block";
        } else {
            cursoSuapExibicao.textContent = "";
            cursoSuapExibicao.style.display = "none";
        }
    }
}

if (selectDiretoriaManual) {
    selectDiretoriaManual.addEventListener("change", () => {
        if (inputDiretoria) {
            inputDiretoria.value = selectDiretoriaManual.value || "";
        }
    });
}

function atualizarStatusSuap(texto, tipo) {
    if (!suapStatusMsg) return;
    if (!texto) {
        suapStatusMsg.style.display = "none";
        suapStatusMsg.textContent = "";
        suapStatusMsg.className = "suap-status-msg";
        return;
    }
    suapStatusMsg.textContent = texto;
    suapStatusMsg.className = "suap-status-msg" + (tipo === "ok" ? " suap-ok" : tipo === "erro" ? " suap-erro" : "");
    suapStatusMsg.style.display = "block";
}

// Inicializa diretoria caso venha por parâmetro na URL (?diretoria=...)
(function() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const dirParam = urlParams.get("diretoria");
        if (dirParam && (!inputDiretoria || !inputDiretoria.value)) {
            const dirFormatada = dirParam.charAt(0).toUpperCase() + dirParam.slice(1).toLowerCase();
            if (["Diatinf", "Diaren", "Diacon", "Diacin"].includes(dirFormatada)) {
                definirDiretoriaNoFormulario(dirFormatada, "", false);
            }
        }
    } catch (e) {}
})();

async function fetchSuapJson(url, token) {
    const esquemas = ["Bearer", "JWT"];
    for (let i = 0; i < esquemas.length; i++) {
        try {
            const r = await fetch(url, {
                method: "GET",
                headers: {
                    "Authorization": esquemas[i] + " " + token,
                    "Accept": "application/json",
                },
            });
            if (r.status === 200) {
                return await r.json();
            }
            if (r.status !== 401) {
                return null;
            }
        } catch (e) {
            return null;
        }
    }
    return null;
}

function extrairListaSuapJs(dados) {
    if (Array.isArray(dados)) return dados;
    if (dados && Array.isArray(dados.results)) return dados.results;
    return [];
}

/**
 * Consulta o SUAP oficial diretamente pelo navegador do aluno (via CORS liberado em suap.ifrn.edu.br),
 * garantindo dados reais inclusive em hospedagens gratuitas com proxy restrito no servidor.
 */
async function consultarSuapDiretoNoNavegador(matricula, senha) {
    try {
        const respToken = await fetch("https://suap.ifrn.edu.br/api/token/pair", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            body: JSON.stringify({ username: matricula, password: senha }),
        });

        if (respToken.status === 400 || respToken.status === 401) {
            return {
                disponivel: true,
                credenciais_invalidas: true,
                erro: "Matrícula ou senha do SUAP incorreta.",
            };
        }
        if (!respToken.ok) {
            return { disponivel: false };
        }

        const corpoToken = await respToken.json();
        const token = corpoToken && (corpoToken.access || corpoToken.token);
        if (!token) {
            return { disponivel: false };
        }

        const [eu, dadosAluno, alunoMat, alunoResumido, vinculos] = await Promise.all([
            fetchSuapJson("https://suap.ifrn.edu.br/api/rh/eu/", token),
            fetchSuapJson("https://suap.ifrn.edu.br/api/ensino/meus-dados-aluno/", token),
            fetchSuapJson("https://suap.ifrn.edu.br/api/ensino/aluno-matriculado/?matricula=" + encodeURIComponent(matricula), token),
            fetchSuapJson("https://suap.ifrn.edu.br/api/ensino/aluno-resumido/?matricula=" + encodeURIComponent(matricula), token),
            fetchSuapJson("https://suap.ifrn.edu.br/api/rh/meus-vinculos/", token),
        ]);

        let nome = "";
        let matOficial = matricula;
        if (eu && typeof eu === "object") {
            nome = eu.nome_usual || eu.nome || eu.nome_registro || "";
            if (eu.identificacao) matOficial = String(eu.identificacao);
        }

        let curso = "";
        let diretoria = "";
        if (dadosAluno && typeof dadosAluno === "object" && dadosAluno.curso) {
            curso = String(dadosAluno.curso);
        }
        if (!curso && alunoMat && typeof alunoMat === "object" && alunoMat.curso) {
            curso = String(alunoMat.curso);
        }
        if (!nome && alunoMat && alunoMat.nome) {
            nome = String(alunoMat.nome);
        }

        const listaResumida = extrairListaSuapJs(alunoResumido);
        for (let i = 0; i < listaResumida.length; i++) {
            const al = listaResumida[i] && (listaResumida[i].aluno || listaResumida[i]);
            if (al && typeof al === "object") {
                if (!curso && al.curso) curso = String(al.curso);
                if (!diretoria && al.diretoria) diretoria = String(al.diretoria);
                if (!nome && al.nome) nome = String(al.nome);
            }
        }

        if (!curso) {
            const listaVinc = extrairListaSuapJs(vinculos);
            for (let i = 0; i < listaVinc.length; i++) {
                const v = listaVinc[i];
                if (v && v.detalhamento && v.detalhamento.curso) {
                    curso = String(v.detalhamento.curso);
                    break;
                }
            }
        }

        const extras = [];
        if (!curso && !diretoria) {
            const periodosRaw = await fetchSuapJson("https://suap.ifrn.edu.br/api/ensino/meus-periodos-letivos/", token);
            const periodos = extrairListaSuapJs(periodosRaw);
            if (periodos.length > 0) {
                const ultimo = periodos[periodos.length - 1];
                if (ultimo && ultimo.ano_letivo && ultimo.periodo_letivo) {
                    const ano = ultimo.ano_letivo;
                    const per = ultimo.periodo_letivo;
                    const boletimRaw = await fetchSuapJson(`https://suap.ifrn.edu.br/api/ensino/meu-boletim/${ano}/${per}/`, token);
                    const turmasRaw = await fetchSuapJson(`https://suap.ifrn.edu.br/api/ensino/minhas-turmas-virtuais/${ano}/${per}/`, token);
                    extrairListaSuapJs(boletimRaw).concat(extrairListaSuapJs(turmasRaw)).slice(0, 15).forEach(it => {
                        if (it && typeof it === "object") {
                            const txt = [it.disciplina, it.descricao, it.sigla, it.codigo_diario].filter(Boolean).join(" ");
                            if (txt) extras.push(txt);
                        }
                    });
                }
            }
        }

        return {
            disponivel: true,
            verificado: true,
            credenciais_invalidas: false,
            matricula_oficial: matOficial,
            nome: nome,
            curso: curso,
            diretoria: diretoria,
            extras: extras.join(" | "),
        };
    } catch (e) {
        return { disponivel: false };
    }
}

async function executarConsultaSuap(incluirSenha) {
    if (!inputMatriculaCadastro) return null;
    const mat = (inputMatriculaCadastro.value || "").trim();
    if (mat.length < 8) {
        autenticacaoSuapValidada = false;
        credenciaisSuapInvalidas = false;
        limparCamposClienteSuap();
        definirDiretoriaNoFormulario("", "", false);
        atualizarStatusSuap("", "");
        return null;
    }

    const dirLocal = identificarDiretoriaLocal(mat);
    if (dirLocal && !autenticacaoSuapValidada) {
        definirDiretoriaNoFormulario(dirLocal, "", false);
    }

    const senhaValor = (incluirSenha && inputSenhaCadastro && inputSenhaCadastro.value) ? inputSenhaCadastro.value : "";

    if (senhaValor.length >= 6) {
        atualizarStatusSuap("Consultando seus dados no SUAP...", "");
        const cli = await consultarSuapDiretoNoNavegador(mat, senhaValor);

        if (cli && cli.disponivel && cli.credenciais_invalidas) {
            autenticacaoSuapValidada = false;
            credenciaisSuapInvalidas = true;
            limparCamposClienteSuap();
            alternarModoEscolhaDiretoria(false);
            atualizarStatusSuap(cli.erro || "Matrícula ou senha do SUAP incorreta.", "erro");
            return { credenciais_invalidas: true, erro: cli.erro };
        }

        const body = new URLSearchParams();
        body.set("matricula", (cli && cli.matricula_oficial) ? cli.matricula_oficial : mat);
        body.set("senha", senhaValor);
        if (cli && cli.verificado) {
            preencherCamposClienteSuap(cli);
            body.set("suap_verificado_cliente", "1");
            body.set("suap_nome", cli.nome || "");
            body.set("suap_curso", cli.curso || "");
            body.set("suap_diretoria", cli.diretoria || "");
            body.set("suap_extras", cli.extras || "");
        } else {
            limparCamposClienteSuap();
        }

        try {
            const resp = await fetch("/api/suap/verificar/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-CSRFToken": obterCsrfCadastro(),
                    "Accept": "application/json",
                },
                body: body.toString(),
            });
            const dados = await resp.json();
            if (!dados) return null;
            ultimaChaveConsultada = mat + "::" + senhaValor;

            if (dados.credenciais_invalidas) {
                autenticacaoSuapValidada = false;
                credenciaisSuapInvalidas = true;
                limparCamposClienteSuap();
                alternarModoEscolhaDiretoria(false);
                atualizarStatusSuap(dados.erro || "Matrícula ou senha do SUAP incorreta.", "erro");
                return dados;
            }

            credenciaisSuapInvalidas = false;
            if (dados.autenticado_suap) {
                autenticacaoSuapValidada = true;
                const dirFinal = dados.diretoria || dirLocal || "";
                const permitirManual = !!dados.permitir_escolha_manual && !dirFinal;
                definirDiretoriaNoFormulario(dirFinal, dados.curso || "", permitirManual);
                const resumo = [dados.nome, dirFinal].filter(Boolean).join(" — ");
                if (dirFinal) {
                    atualizarStatusSuap(
                        resumo ? ("✓ SUAP: " + resumo) : "✓ Dados confirmados no SUAP!",
                        "ok"
                    );
                } else {
                    atualizarStatusSuap("✓ Conta autenticada no SUAP. Selecione sua diretoria abaixo.", "ok");
                }
            } else {
                autenticacaoSuapValidada = false;
                const dirFb = dados.diretoria || dirLocal || "";
                const permitirManual = !!dados.permitir_escolha_manual && !dirFb;
                definirDiretoriaNoFormulario(dirFb, dados.curso || "", permitirManual);
                if (dados.offline) {
                    if (dirFb) {
                        atualizarStatusSuap("✓ Diretoria identificada: " + dirFb, "ok");
                    } else {
                        atualizarStatusSuap("Selecione sua diretoria abaixo para concluir.", "");
                    }
                } else if (dados.erro) {
                    atualizarStatusSuap(dados.erro, "erro");
                }
            }
            return dados;
        } catch (err) {
            return null;
        }
    }

    try {
        const params = new URLSearchParams();
        params.set("matricula", mat);
        const r = await fetch("/api/suap/verificar/?" + params.toString(), {
            method: "GET",
            headers: { "Accept": "application/json" }
        });
        const dados = await r.json();
        if (dados && dados.diretoria && !autenticacaoSuapValidada) {
            definirDiretoriaNoFormulario(dados.diretoria, dados.curso || "", false);
        } else if (!dirLocal && !autenticacaoSuapValidada && (!selectDiretoriaManual || selectDiretoriaManual.style.display === "none")) {
            definirDiretoriaNoFormulario("", "", false);
        }
    } catch (e) {}
    return null;
}

function consultarSuapAutomatico(incluirSenha) {
    verificacaoEmCursoPromise = executarConsultaSuap(incluirSenha).finally(() => {
        verificacaoEmCursoPromise = null;
    });
    return verificacaoEmCursoPromise;
}

if (inputMatriculaCadastro) {
    inputMatriculaCadastro.addEventListener("input", () => {
        autenticacaoSuapValidada = false;
        credenciaisSuapInvalidas = false;
        ultimaChaveConsultada = "";
        limparCamposClienteSuap();
        const mat = (inputMatriculaCadastro.value || "").trim();
        const dirLocal = identificarDiretoriaLocal(mat);
        if (dirLocal) {
            definirDiretoriaNoFormulario(dirLocal, "", false);
        } else if (mat.length < 8) {
            definirDiretoriaNoFormulario("", "", false);
        }
        clearTimeout(timerConsultaSuap);
        const temSenha = !!(inputSenhaCadastro && inputSenhaCadastro.value.length >= 6);
        timerConsultaSuap = setTimeout(() => consultarSuapAutomatico(temSenha), 300);
    });
    inputMatriculaCadastro.addEventListener("blur", () => {
        consultarSuapAutomatico(true);
    });
}

if (inputSenhaCadastro) {
    inputSenhaCadastro.addEventListener("input", () => {
        autenticacaoSuapValidada = false;
        credenciaisSuapInvalidas = false;
        ultimaChaveConsultada = "";
        limparCamposClienteSuap();
        if (inputMatriculaCadastro && inputMatriculaCadastro.value.trim().length >= 8 && inputSenhaCadastro.value.length >= 6) {
            clearTimeout(timerConsultaSuap);
            timerConsultaSuap = setTimeout(() => consultarSuapAutomatico(true), 450);
        }
    });
    inputSenhaCadastro.addEventListener("blur", () => {
        if (inputMatriculaCadastro && inputMatriculaCadastro.value.trim().length >= 8 && inputSenhaCadastro.value.length >= 6) {
            consultarSuapAutomatico(true);
        }
    });
}

if (formCadastro) {
    formCadastro.addEventListener("submit", async (e) => {
        const mat = inputMatriculaCadastro ? inputMatriculaCadastro.value.trim() : "";
        const senhaVal = inputSenhaCadastro ? inputSenhaCadastro.value : "";
        const chaveAtual = mat + "::" + senhaVal;

        if (credenciaisSuapInvalidas) {
            e.preventDefault();
            const btnInv = formCadastro.querySelector("button[type='submit']");
            setTimeout(() => {
                if (btnInv) btnInv.disabled = false;
            }, 15);
            if (inputSenhaCadastro) inputSenhaCadastro.focus();
            return;
        }
        if (mat.length >= 8 && senhaVal.length >= 6 && (ultimaChaveConsultada !== chaveAtual || verificacaoEmCursoPromise)) {
            e.preventDefault();
            const btn = formCadastro.querySelector("button[type='submit']");
            const txtOrig = btn ? btn.textContent : "";
            const reabilitarBotao = () => {
                if (btn) {
                    btn.disabled = false;
                    btn.textContent = txtOrig;
                }
            };
            if (btn) {
                btn.disabled = true;
                btn.textContent = "Verificando...";
            }
            const res = verificacaoEmCursoPromise
                ? await verificacaoEmCursoPromise
                : await consultarSuapAutomatico(true);
            reabilitarBotao();
            if (res && res.credenciais_invalidas) {
                setTimeout(reabilitarBotao, 15);
                return;
            }
            if (res && res.permitir_escolha_manual && !(inputDiretoria && inputDiretoria.value)) {
                setTimeout(reabilitarBotao, 15);
                return;
            }
            HTMLFormElement.prototype.submit.call(formCadastro);
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
