/* ==========================================================
   1) Button-UI während der Analyse
   ========================================================== */

document.addEventListener("DOMContentLoaded", function () {
    const form = document.getElementById("analyseForm");
    const button = document.getElementById("analyseButton");

    if (!form || !button) return;

    form.addEventListener("submit", function () {
        button.disabled = true;
        button.value = "Analyse läuft…";
    });
});


/* ==========================================================
   2) HTML5UP: Autoclose verhindern
   ========================================================== */

document.addEventListener("DOMContentLoaded", function () {
    const wrapper = document.getElementById("wrapper");
    const main = document.getElementById("main");

    if (!wrapper || !main) return;

    wrapper.addEventListener("click", function (event) {
        if (document.body.classList.contains("is-article-visible")) {
            if (!main.contains(event.target)) {
                event.stopPropagation();
                event.preventDefault();
                return false;
            }
        }
    }, true);
});


/* ==========================================================
   3) Analyseergebnisse anzeigen + Artikel öffnen
   ========================================================== */

document.addEventListener("DOMContentLoaded", () => {
    const result = document.getElementById("analysis-result");

    if (result && result.innerHTML.trim().length > 0) {
        setTimeout(() => {
            location.hash = "#analyse";
        }, 150);
    }
});


