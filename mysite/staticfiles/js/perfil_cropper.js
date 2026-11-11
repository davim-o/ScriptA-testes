/**
 * Enquadrador interativo de foto de perfil (1:1 circular) e banner (3:1) com HTML5 Canvas.
 * Permite arrastar, dar zoom (slider/scroll), rotacionar 90° e aplicar o recorte direto no input[type="file"].
 */
(function () {
    "use strict";

    var estado = {
        ativo: false,
        modo: "foto", // "foto" | "banner"
        inputEl: null,
        imagem: null,
        nomeBase: "imagem",
        zoom: 1,
        rotacao: 0,
        offsetX: 0,
        offsetY: 0,
        arrastando: false,
        ultimoX: 0,
        ultimoY: 0,
        onAplicar: null,
    };

    var fontesOriginais = {
        foto: "",
        banner: "",
    };

    var objectUrlsCriadas = [];

    function criarObjectUrl(blobOuFile) {
        var u = URL.createObjectURL(blobOuFile);
        objectUrlsCriadas.push(u);
        return u;
    }

    window.addEventListener("beforeunload", function () {
        objectUrlsCriadas.forEach(function (u) {
            try { URL.revokeObjectURL(u); } catch (_) {}
        });
    });

    function obterElementos() {
        return {
            backdrop: document.getElementById("modal-cropper-backdrop"),
            titulo: document.getElementById("cropper-titulo"),
            palco: document.getElementById("cropper-palco"),
            canvas: document.getElementById("cropper-canvas"),
            guia: document.getElementById("cropper-guia"),
            sliderZoom: document.getElementById("cropper-zoom"),
            valorZoom: document.getElementById("cropper-zoom-valor"),
            btnRotar: document.getElementById("btn-cropper-rotar"),
            btnReset: document.getElementById("btn-cropper-reset"),
            btnFechar: document.getElementById("btn-cropper-fechar"),
            btnCancelar: document.getElementById("btn-cropper-cancelar"),
            btnAplicar: document.getElementById("btn-cropper-aplicar"),
        };
    }

    function dimensoesRotacionadas(img, rotacao) {
        var norm = ((rotacao % 360) + 360) % 360;
        if (norm === 90 || norm === 270) {
            return { w: img.naturalHeight || img.height, h: img.naturalWidth || img.width };
        }
        return { w: img.naturalWidth || img.width, h: img.naturalHeight || img.height };
    }

    function limitarDeslocamento(canvas) {
        if (!estado.imagem || !canvas) return;
        var dims = dimensoesRotacionadas(estado.imagem, estado.rotacao);
        if (!dims.w || !dims.h) return;
        var baseScale = Math.max(canvas.width / dims.w, canvas.height / dims.h);
        var scale = baseScale * estado.zoom;
        var maxX = Math.max(0, (dims.w * scale - canvas.width) / 2);
        var maxY = Math.max(0, (dims.h * scale - canvas.height) / 2);
        estado.offsetX = Math.max(-maxX, Math.min(maxX, estado.offsetX));
        estado.offsetY = Math.max(-maxY, Math.min(maxY, estado.offsetY));
    }

    function desenharCanvas() {
        var els = obterElementos();
        var canvas = els.canvas;
        if (!canvas || !estado.imagem) return;
        var ctx = canvas.getContext("2d");
        if (!ctx) return;

        limitarDeslocamento(canvas);

        ctx.save();
        ctx.fillStyle = "#181c32";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        var dims = dimensoesRotacionadas(estado.imagem, estado.rotacao);
        var baseScale = Math.max(canvas.width / dims.w, canvas.height / dims.h);
        var scale = baseScale * estado.zoom;

        ctx.translate(canvas.width / 2 + estado.offsetX, canvas.height / 2 + estado.offsetY);
        ctx.rotate((estado.rotacao * Math.PI) / 180);
        ctx.scale(scale, scale);
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = "high";
        ctx.drawImage(
            estado.imagem,
            -(estado.imagem.naturalWidth || estado.imagem.width) / 2,
            -(estado.imagem.naturalHeight || estado.imagem.height) / 2
        );
        ctx.restore();
    }

    function fecharCropper() {
        var els = obterElementos();
        estado.ativo = false;
        estado.arrastando = false;
        if (els.backdrop) {
            els.backdrop.classList.remove("aberto");
            els.backdrop.setAttribute("aria-hidden", "true");
        }
    }

    function abrirCropperComSrc(opts) {
        var els = obterElementos();
        if (!els.backdrop || !els.canvas || !opts || !opts.src) return;

        var img = new Image();
        img.onload = function () {
            estado.ativo = true;
            estado.modo = opts.modo || "foto";
            estado.inputEl = opts.inputEl || null;
            estado.imagem = img;
            estado.nomeBase = opts.nomeBase || (estado.modo === "banner" ? "banner_perfil" : "foto_perfil");
            estado.zoom = 1;
            estado.rotacao = 0;
            estado.offsetX = 0;
            estado.offsetY = 0;
            estado.onAplicar = typeof opts.onAplicar === "function" ? opts.onAplicar : null;

            if (estado.modo === "banner") {
                els.canvas.width = 1200;
                els.canvas.height = 400;
                if (els.palco) {
                    els.palco.classList.remove("modo-foto");
                    els.palco.classList.add("modo-banner");
                }
                if (els.guia) {
                    els.guia.classList.remove("guia-circular");
                    els.guia.classList.add("guia-banner");
                }
                if (els.titulo) els.titulo.textContent = "Enquadrar banner do perfil";
            } else {
                els.canvas.width = 560;
                els.canvas.height = 560;
                if (els.palco) {
                    els.palco.classList.remove("modo-banner");
                    els.palco.classList.add("modo-foto");
                }
                if (els.guia) {
                    els.guia.classList.remove("guia-banner");
                    els.guia.classList.add("guia-circular");
                }
                if (els.titulo) els.titulo.textContent = "Enquadrar foto de perfil";
            }

            if (els.sliderZoom) els.sliderZoom.value = "1";
            if (els.valorZoom) els.valorZoom.textContent = "1.0x";

            desenharCanvas();
            els.backdrop.classList.add("aberto");
            els.backdrop.setAttribute("aria-hidden", "false");
        };
        img.onerror = function () {
            if (typeof toast === "function") {
                toast("Não foi possível carregar a imagem para enquadramento.", "erro");
            }
        };
        img.src = opts.src;
    }

    function aplicarRecorte() {
        var els = obterElementos();
        var canvas = els.canvas;
        if (!canvas || !estado.imagem) return;

        desenharCanvas();
        var tipoSaida = "image/jpeg";
        var qualidade = estado.modo === "banner" ? 0.90 : 0.92;
        var nomeLimpo = (estado.nomeBase || "imagem").replace(/\.[^.]+$/, "").replace(/[^a-zA-Z0-9_-]+/g, "_");
        if (!nomeLimpo) nomeLimpo = estado.modo;
        var nomeFinal = nomeLimpo + "_enquadrada.jpg";

        canvas.toBlob(function (blob) {
            if (!blob) {
                if (typeof toast === "function") {
                    toast("Falha ao gerar imagem recortada.", "erro");
                }
                return;
            }
            var arquivo = new File([blob], nomeFinal, { type: tipoSaida, lastModified: Date.now() });
            if (estado.inputEl && typeof DataTransfer !== "undefined") {
                try {
                    var dt = new DataTransfer();
                    dt.items.add(arquivo);
                    estado.inputEl.files = dt.files;
                } catch (_) {}
            }
            var previewUrl = criarObjectUrl(blob);
            if (estado.onAplicar) {
                estado.onAplicar(previewUrl, arquivo);
            }
            fecharCropper();
            if (typeof toast === "function") {
                toast("Enquadramento aplicado! Clique em \"Salvar alterações\" para confirmar.", "sucesso");
            }
        }, tipoSaida, qualidade);
    }

    function iniciarEventosCropper() {
        var els = obterElementos();
        if (!els.backdrop || !els.canvas) return;

        function iniciarArraste(clientX, clientY) {
            if (!estado.ativo) return;
            estado.arrastando = true;
            estado.ultimoX = clientX;
            estado.ultimoY = clientY;
        }

        function moverArraste(clientX, clientY) {
            if (!estado.ativo || !estado.arrastando) return;
            var rect = els.canvas.getBoundingClientRect();
            if (!rect.width || !rect.height) return;
            var fatorX = els.canvas.width / rect.width;
            var fatorY = els.canvas.height / rect.height;
            estado.offsetX += (clientX - estado.ultimoX) * fatorX;
            estado.offsetY += (clientY - estado.ultimoY) * fatorY;
            estado.ultimoX = clientX;
            estado.ultimoY = clientY;
            desenharCanvas();
        }

        function encerrarArraste() {
            estado.arrastando = false;
        }

        els.palco.addEventListener("mousedown", function (e) {
            e.preventDefault();
            iniciarArraste(e.clientX, e.clientY);
        });
        window.addEventListener("mousemove", function (e) {
            if (estado.arrastando) moverArraste(e.clientX, e.clientY);
        });
        window.addEventListener("mouseup", encerrarArraste);

        els.palco.addEventListener("touchstart", function (e) {
            if (e.touches && e.touches.length === 1) {
                e.preventDefault();
                iniciarArraste(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: false });
        els.palco.addEventListener("touchmove", function (e) {
            if (estado.arrastando && e.touches && e.touches.length === 1) {
                e.preventDefault();
                moverArraste(e.touches[0].clientX, e.touches[0].clientY);
            }
        }, { passive: false });
        window.addEventListener("touchend", encerrarArraste);

        els.palco.addEventListener("wheel", function (e) {
            if (!estado.ativo) return;
            e.preventDefault();
            var passo = e.deltaY < 0 ? 0.1 : -0.1;
            var novoZoom = Math.max(1, Math.min(3, estado.zoom + passo));
            estado.zoom = Math.round(novoZoom * 100) / 100;
            if (els.sliderZoom) els.sliderZoom.value = String(estado.zoom);
            if (els.valorZoom) els.valorZoom.textContent = estado.zoom.toFixed(1) + "x";
            desenharCanvas();
        }, { passive: false });

        if (els.sliderZoom) {
            els.sliderZoom.addEventListener("input", function () {
                estado.zoom = Math.max(1, Math.min(3, parseFloat(this.value) || 1));
                if (els.valorZoom) els.valorZoom.textContent = estado.zoom.toFixed(1) + "x";
                desenharCanvas();
            });
        }

        if (els.btnRotar) {
            els.btnRotar.addEventListener("click", function () {
                estado.rotacao = (estado.rotacao + 90) % 360;
                estado.offsetX = 0;
                estado.offsetY = 0;
                desenharCanvas();
            });
        }

        if (els.btnReset) {
            els.btnReset.addEventListener("click", function () {
                estado.zoom = 1;
                estado.rotacao = 0;
                estado.offsetX = 0;
                estado.offsetY = 0;
                if (els.sliderZoom) els.sliderZoom.value = "1";
                if (els.valorZoom) els.valorZoom.textContent = "1.0x";
                desenharCanvas();
            });
        }

        if (els.btnFechar) els.btnFechar.addEventListener("click", fecharCropper);
        if (els.btnCancelar) els.btnCancelar.addEventListener("click", fecharCropper);
        if (els.btnAplicar) els.btnAplicar.addEventListener("click", aplicarRecorte);

        els.backdrop.addEventListener("click", function (e) {
            if (e.target === els.backdrop) fecharCropper();
        });

        window.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && estado.ativo) {
                fecharCropper();
            }
        });
    }

    function vincularControlesPerfil() {
        var inputFoto = document.getElementById("input-foto-perfil");
        var btnEnquadrarFoto = document.getElementById("btn-enquadrar-foto");
        var previewAvatar = document.getElementById("preview-avatar-edicao");
        var nomeFoto = document.getElementById("nome-arquivo-foto");
        var checkRemoverFoto = document.getElementById("check-remover-foto");

        var inputBanner = document.getElementById("input-banner-perfil");
        var btnEnquadrarBanner = document.getElementById("btn-enquadrar-banner");
        var previewBanner = document.getElementById("preview-banner-edicao");
        var nomeBanner = document.getElementById("nome-arquivo-banner");
        var checkRemoverBanner = document.getElementById("check-remover-banner");

        if (window.fotoOriginalUrl) {
            fontesOriginais.foto = window.fotoOriginalUrl;
        }
        if (window.bannerOriginalUrl) {
            fontesOriginais.banner = window.bannerOriginalUrl;
        }

        function atualizarPreviewAvatar(url, textoStatus) {
            if (previewAvatar) {
                previewAvatar.textContent = "";
                var img = document.createElement("img");
                img.src = url;
                img.alt = "Preview da foto";
                img.className = "perfil-foto-img";
                previewAvatar.appendChild(img);
            }
            if (checkRemoverFoto) checkRemoverFoto.checked = false;
            if (btnEnquadrarFoto) btnEnquadrarFoto.style.display = "inline-flex";
            if (nomeFoto && textoStatus) {
                nomeFoto.textContent = textoStatus;
                nomeFoto.style.color = "#81c784";
            }
        }

        function atualizarPreviewBanner(url, textoStatus) {
            if (previewBanner) {
                previewBanner.textContent = "";
                var img = document.createElement("img");
                img.src = url;
                img.alt = "Preview do banner";
                img.className = "edicao-banner-img";
                previewBanner.appendChild(img);
            }
            if (checkRemoverBanner) checkRemoverBanner.checked = false;
            if (btnEnquadrarBanner) btnEnquadrarBanner.style.display = "inline-flex";
            if (nomeBanner && textoStatus) {
                nomeBanner.textContent = textoStatus;
                nomeBanner.style.color = "#81c784";
            }
        }

        if (inputFoto) {
            inputFoto.addEventListener("change", function () {
                if (!inputFoto.files || !inputFoto.files[0]) return;
                var file = inputFoto.files[0];
                var url = criarObjectUrl(file);
                fontesOriginais.foto = url;
                atualizarPreviewAvatar(url, "✓ Foto selecionada: " + file.name);
                abrirCropperComSrc({
                    modo: "foto",
                    src: url,
                    inputEl: inputFoto,
                    nomeBase: file.name,
                    onAplicar: function (croppedUrl, croppedFile) {
                        atualizarPreviewAvatar(croppedUrl, "✓ Enquadrada: " + croppedFile.name);
                    },
                });
            });
        }

        if (btnEnquadrarFoto) {
            btnEnquadrarFoto.addEventListener("click", function () {
                var src = fontesOriginais.foto || window.fotoOriginalUrl;
                if (!src) {
                    if (typeof toast === "function") {
                        toast("Escolha uma foto primeiro para enquadrar.", "aviso");
                    }
                    return;
                }
                abrirCropperComSrc({
                    modo: "foto",
                    src: src,
                    inputEl: inputFoto,
                    nomeBase: "foto_perfil",
                    onAplicar: function (croppedUrl, croppedFile) {
                        atualizarPreviewAvatar(croppedUrl, "✓ Enquadrada: " + croppedFile.name);
                    },
                });
            });
        }

        if (inputBanner) {
            inputBanner.addEventListener("change", function () {
                if (!inputBanner.files || !inputBanner.files[0]) return;
                var file = inputBanner.files[0];
                var url = criarObjectUrl(file);
                fontesOriginais.banner = url;
                atualizarPreviewBanner(url, "✓ Banner selecionado: " + file.name);
                abrirCropperComSrc({
                    modo: "banner",
                    src: url,
                    inputEl: inputBanner,
                    nomeBase: file.name,
                    onAplicar: function (croppedUrl, croppedFile) {
                        atualizarPreviewBanner(croppedUrl, "✓ Enquadrado: " + croppedFile.name);
                    },
                });
            });
        }

        if (btnEnquadrarBanner) {
            btnEnquadrarBanner.addEventListener("click", function () {
                var src = fontesOriginais.banner || window.bannerOriginalUrl;
                if (!src) {
                    if (typeof toast === "function") {
                        toast("Escolha uma imagem de banner primeiro para enquadrar.", "aviso");
                    }
                    return;
                }
                abrirCropperComSrc({
                    modo: "banner",
                    src: src,
                    inputEl: inputBanner,
                    nomeBase: "banner_perfil",
                    onAplicar: function (croppedUrl, croppedFile) {
                        atualizarPreviewBanner(croppedUrl, "✓ Enquadrado: " + croppedFile.name);
                    },
                });
            });
        }
    }

    document.addEventListener("DOMContentLoaded", function () {
        iniciarEventosCropper();
        vincularControlesPerfil();
    });

    window.scriptaLimparPreviewCropperFoto = function () {
        fontesOriginais.foto = window.fotoOriginalUrl || "";
        var btn = document.getElementById("btn-enquadrar-foto");
        if (btn && !window.fotoOriginalUrl) btn.style.display = "none";
    };

    window.scriptaLimparPreviewCropperBanner = function () {
        fontesOriginais.banner = window.bannerOriginalUrl || "";
        var btn = document.getElementById("btn-enquadrar-banner");
        if (btn && !window.bannerOriginalUrl) btn.style.display = "none";
    };
})();

