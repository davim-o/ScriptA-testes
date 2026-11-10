(function () {
    // =========================================================================
    // 1. MOVIMENTAÇÃO ORIGINAL DOS OLHOS DOS MASCOTES (Preservada exatamente)
    // =========================================================================
    var container = document.querySelector(".imagens");
    if (container) {
        var olhos = container.querySelectorAll(".olho-mascote");
        var rafId = null;
        var targetX = null;
        var targetY = null;

        function atualizarOlhos() {
            rafId = null;
            if (targetX === null || targetY === null) return;
            if (container.classList.contains("olhos-fechados")) return;

            for (var i = 0; i < olhos.length; i++) {
                var olho = olhos[i];
                var pupila = olho.querySelector(".pupila-mascote");
                if (!pupila) continue;

                var rect = olho.getBoundingClientRect();
                if (!rect.width || !rect.height) continue;

                var cx = rect.left + rect.width / 2;
                var cy = rect.top + rect.height / 2;
                var dx = targetX - cx;
                var dy = targetY - cy;
                var angle = Math.atan2(dy, dx);
                var dist = Math.min(1, Math.hypot(dx, dy) / 130);

                var maxMoveX = rect.width * 0.21;
                var maxMoveY = rect.height * 0.21;

                var moveX = Math.cos(angle) * maxMoveX * dist;
                var moveY = Math.sin(angle) * maxMoveY * dist;

                pupila.style.setProperty("--dx", moveX.toFixed(2) + "px");
                pupila.style.setProperty("--dy", moveY.toFixed(2) + "px");
            }
        }

        function agendarAtualizacao(x, y) {
            targetX = x;
            targetY = y;
            if (!rafId) {
                rafId = window.requestAnimationFrame(atualizarOlhos);
            }
        }

        window.addEventListener("mousemove", function (e) {
            agendarAtualizacao(e.clientX, e.clientY);
        }, { passive: true });

        window.addEventListener("touchstart", function (e) {
            if (e.touches && e.touches.length > 0) {
                agendarAtualizacao(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });

        window.addEventListener("touchmove", function (e) {
            if (e.touches && e.touches.length > 0) {
                agendarAtualizacao(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: true });

        document.addEventListener("focusin", function (e) {
            if (e.target && (e.target.tagName === "INPUT" || e.target.classList.contains("dropdown-btn"))) {
                var r = e.target.getBoundingClientRect();
                agendarAtualizacao(r.left + r.width * 0.35, r.top + r.height / 2);
            }
        });

        window.definirOlhosMascotesFechados = function (fechados) {
            if (fechados) {
                container.classList.add("olhos-fechados");
            } else {
                container.classList.remove("olhos-fechados");
                if (targetX !== null && targetY !== null) {
                    agendarAtualizacao(targetX, targetY);
                }
            }
        };
    }

    // =========================================================================
    // 2. EXIBIÇÃO DO CARD AO CLICAR NO RESPECTIVO MASCOTE
    //    Mapeamento: Diacon = Dragão | Diaren = Cavalo | Diatinf = Tigre | Diacin = Cobra
    // =========================================================================
    var DADOS_DIRETORIAS = {
        "Diatinf": {
            sigla: "DIATINF",
            subtitulo: "Diretoria Acadêmica de Gestão e Tecnologia da Informação • Mascote: Tigre",
            mascoteSrc: "/static/imgs/tigre.png",
            temaClasse: "tema-diatinf",
            descricao: "Responsável pelas áreas de gestão e tecnologia da informação, abrangendo conhecimentos de administração, informática, programação e desenvolvimento de sistemas. Atua na formação de profissionais preparados para trabalhar com processos administrativos e soluções tecnológicas.",
            cursos: [
                "Administração",
                "Informática para Internet",
                "Manutenção e Suporte em Informática"
            ]
        },
        "Diaren": {
            sigla: "DIAREN",
            subtitulo: "Diretoria Acadêmica de Recursos Naturais • Mascote: Cavalo",
            mascoteSrc: "/static/imgs/cavalo.png",
            temaClasse: "tema-diaren",
            descricao: "Responsável pelas áreas relacionadas aos recursos naturais, meio ambiente, geologia e mineração. Sua atuação envolve o estudo, o aproveitamento e a preservação dos recursos naturais, buscando formar profissionais capazes de trabalhar com sustentabilidade e atividades de exploração mineral.",
            cursos: [
                "Controle Ambiental",
                "Geologia",
                "Mineração"
            ]
        },
        "Diacon": {
            sigla: "DIACON",
            subtitulo: "Diretoria Acadêmica de Construção Civil • Mascote: Dragão",
            mascoteSrc: "/static/imgs/dragao.png",
            temaClasse: "tema-diacon",
            descricao: "Responsável pela área de construção civil, envolvendo conhecimentos sobre projetos, edificações, materiais, planejamento e execução de obras. Prepara profissionais para atuar nas diferentes etapas dos processos construtivos, desde o planejamento até o acompanhamento das construções.",
            cursos: [
                "Edificações"
            ]
        },
        "Diacin": {
            sigla: "DIACIN",
            subtitulo: "Diretoria Acadêmica de Indústria • Mascote: Cobra",
            mascoteSrc: "/static/imgs/cobra.png",
            temaClasse: "tema-diacin",
            descricao: "Responsável pela formação profissional na área industrial, abrangendo conhecimentos de eletricidade, mecânica, máquinas, equipamentos e processos de produção. Busca preparar estudantes para atuar na instalação, operação e manutenção de sistemas e equipamentos industriais.",
            cursos: [
                "Eletrotécnica",
                "Mecânica"
            ]
        }
    };

    var modalBackdrop = document.getElementById("mascoteModalBackdrop");
    var mascoteCard = document.getElementById("mascoteCard");
    var btnFechar = document.getElementById("btnFecharMascoteCard");
    var heroImg = document.getElementById("mascoteHeroImg");
    var elNome = document.getElementById("mascoteNomeDiretoria");
    var elSubtitulo = document.getElementById("mascoteSubtitulo");
    var elDescricao = document.getElementById("mascoteDescricao");
    var elListaCursos = document.getElementById("mascoteListaCursos");
    var btnAcao = document.getElementById("btnAcaoDiretoria");
    var textoBtnAcao = document.getElementById("textoBtnAcao");

    function abrirCardMascote(chave) {
        if (!modalBackdrop || !mascoteCard) return;
        var info = DADOS_DIRETORIAS[chave];
        if (!info) return;

        mascoteCard.className = "mascote-card " + info.temaClasse;

        if (heroImg) {
            heroImg.src = info.mascoteSrc;
            heroImg.alt = info.sigla;
        }
        if (elNome) elNome.textContent = info.sigla;
        if (elSubtitulo) elSubtitulo.textContent = info.subtitulo;
        if (elDescricao) elDescricao.textContent = info.descricao;

        if (elListaCursos) {
            elListaCursos.innerHTML = "";
            info.cursos.forEach(function (c) {
                var li = document.createElement("li");
                li.textContent = c;
                elListaCursos.appendChild(li);
            });
        }

        var inputDiretoria = document.getElementById("diretoriaSelecionada");
        var formCadastro = document.getElementById("form-cadastro");

        if (formCadastro && inputDiretoria) {
            if (textoBtnAcao) textoBtnAcao.textContent = "Selecionar " + info.sigla;
            btnAcao.onclick = function () {
                inputDiretoria.value = chave;
                fecharCardMascote();
            };
        } else {
            if (textoBtnAcao) textoBtnAcao.textContent = "Fazer cadastro na " + info.sigla;
            btnAcao.onclick = function () {
                window.location.href = "/cadastro/?diretoria=" + encodeURIComponent(chave);
            };
        }

        modalBackdrop.classList.add("aberto");
        modalBackdrop.setAttribute("aria-hidden", "false");
    }

    function fecharCardMascote() {
        if (!modalBackdrop) return;
        modalBackdrop.classList.remove("aberto");
        modalBackdrop.setAttribute("aria-hidden", "true");
    }

    if (btnFechar) {
        btnFechar.addEventListener("click", fecharCardMascote);
    }

    if (modalBackdrop) {
        modalBackdrop.addEventListener("click", function (e) {
            if (e.target === modalBackdrop) fecharCardMascote();
        });
    }

    window.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && modalBackdrop && modalBackdrop.classList.contains("aberto")) {
            fecharCardMascote();
        }
    });

    // Vincula cada mascote ao clique
    var mascotes = [
        { seletor: ".mascote-tigre", diretoria: "Diatinf" },
        { seletor: ".mascote-dragao", diretoria: "Diacon" },
        { seletor: ".mascote-cavalo", diretoria: "Diaren" },
        { seletor: ".mascote-cobra", diretoria: "Diacin" }
    ];

    mascotes.forEach(function (item) {
        var el = document.querySelector(item.seletor);
        if (el) {
            el.addEventListener("click", function () {
                abrirCardMascote(item.diretoria);
            });
        }
    });
})();
