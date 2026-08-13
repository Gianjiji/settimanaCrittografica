(function () {
  "use strict";

  function readAnswers(form) {
    return Array.prototype.map.call(form.querySelectorAll("input"), function (input) {
      return input.value;
    });
  }

  function post(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).then(function (response) { return response.json(); });
  }

  function markFields(form, fields) {
    var inputs = form.querySelectorAll("input");
    Array.prototype.forEach.call(inputs, function (input, index) {
      var ok = fields ? fields[index] : true;
      input.classList.toggle("errato", !ok);
    });
  }

  function firstWrongInput(form, fields) {
    var inputs = form.querySelectorAll("input");
    for (var index = 0; index < inputs.length; index += 1) {
      if (!fields || !fields[index]) { return inputs[index]; }
    }
    return inputs[0] || null;
  }

  function focusForRetry(form, fields) {
    // After a wrong answer the caret belongs in the field to fix, not wherever it was
    // left, so the next keystroke starts the correction.
    var target = firstWrongInput(form, fields);
    if (!target) { return; }
    target.focus();
    if (typeof target.select === "function") { target.select(); }
  }

  document.querySelectorAll("form.risposta").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var esito = form.querySelector(".esito");
      var isWord = form.classList.contains("parola");
      var url = isWord ? "/api/parola" : "/api/verifica";
      var payload = { issue: form.dataset.issue };
      if (isWord) {
        payload.answer = form.querySelector("input").value;
      } else {
        payload.number = parseInt(form.dataset.number, 10);
        payload.answers = readAnswers(form);
      }
      esito.textContent = "Controllo in corso";
      post(url, payload).then(function (data) {
        if (data.error) {
          esito.textContent = data.error;
          return;
        }
        markFields(form, data.fields);
        if (data.correct) {
          esito.textContent = "";
          var card = form.closest(".scheda") || form.closest(".sezione");
          if (card) { card.classList.add("risolta"); }
          if (isWord) { esito.textContent = "Parola esatta. Fascicolo chiuso."; }
        } else {
          esito.textContent = isWord
            ? "Non e' questa. Ricontrolla la somma delle nove risposte."
            : "Non torna. Rileggi l'aiuto 2 prima di riprovare.";
          focusForRetry(form, data.fields);
        }
      }).catch(function () {
        esito.textContent = "Verifica non disponibile offline.";
      });
    });
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () { });
    });
  }
})();
