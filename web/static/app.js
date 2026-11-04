// KaTeX sobre toda la pagina (delimitadores $...$, $$...$$, \(...\), \[...\]) y pequenos
// detalles de uso. Nada de aqui habla con el servidor: todo el trabajo esta en nucleo/.
document.addEventListener("DOMContentLoaded", function () {
  if (window.renderMathInElement) {
    try {
      renderMathInElement(document.body, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false },
          { left: "$", right: "$", display: false },
        ],
        throwOnError: false,          // macros privadas del paper: se ven en rojo, no rompen la pagina
        strict: "ignore",
        ignoredTags: ["script", "noscript", "style", "textarea", "pre", "code", "option", "input"],
        ignoredClasses: ["crudo", "consola"],
      });
    } catch (e) {
      console.warn("KaTeX:", e);
    }
  }

  // abrir / cerrar todos los bloques R de una nota
  document.querySelectorAll("[data-plegar]").forEach(function (a) {
    a.addEventListener("click", function (ev) {
      ev.preventDefault();
      var abrir = a.dataset.plegar === "abrir";
      document.querySelectorAll("details.bloque").forEach(function (d) { d.open = abrir; });
    });
  });

  // el formulario de preguntar: Ctrl+Enter envia; un solo envio por respuesta (cada uno se paga)
  var turno = document.getElementById("turno");
  if (turno) {
    turno.addEventListener("submit", function () {
      turno.querySelectorAll("button[type=submit]").forEach(function (b) { b.disabled = true; });
    });
    turno.querySelectorAll("textarea").forEach(function (t) {
      t.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" && (ev.ctrlKey || ev.metaKey)) {
          ev.preventDefault();
          turno.requestSubmit(turno.querySelector("button[value=preguntar]"));
        }
      });
    });
  }
});
