(function () {
    var container = document.querySelector(".imagens");
    if (!container) return;

    var olhos = container.querySelectorAll(".olho-mascote");
    if (!olhos.length) return;

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
})();

