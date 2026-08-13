(function () {
  "use strict";

  function readAnswers(form) {
    return Array.prototype.map.call(form.querySelectorAll("input"), function (input) {
      return input.value;
    });
  }

  // Why a check did not happen. Kept apart from a wrong answer, which is a real verdict.
  var OFFLINE = "offline";
  var SERVER = "server";

  function post(url, payload) {
    return fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    }).catch(function () {
      throw OFFLINE;  // the request never reached the server
    }).then(function (response) {
      return response.json().catch(function () {
        throw SERVER;  // it answered, but not with the JSON we asked for
      }).then(function (data) {
        // A refusal carrying an explanation is an answer; anything else is a failure.
        if (!response.ok && !data.error) { throw SERVER; }
        return data;
      });
    });
  }

  function markFields(form, fields) {
    var inputs = form.querySelectorAll("input");
    Array.prototype.forEach.call(inputs, function (input, index) {
      var ok = fields ? fields[index] : true;
      input.classList.toggle("errato", !ok);
      // The colour alone says nothing to a screen reader, or to anyone who cannot
      // tell it apart, so the state travels with the field itself.
      if (ok) {
        input.removeAttribute("aria-invalid");
      } else {
        input.setAttribute("aria-invalid", "true");
      }
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

  function refreshCounter() {
    // Recounted from the cards themselves: no tally to keep in step, so it cannot drift.
    var counter = document.querySelector(".contatore");
    if (!counter) { return; }
    var total = document.querySelectorAll(".scheda").length;
    var done = document.querySelectorAll(".scheda.risolta").length;
    counter.textContent = done + " di " + total + " schede risolte";
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
          if (card) { card.classList.add("risolta"); refreshCounter(); }
          if (isWord) { esito.textContent = "Parola esatta. Fascicolo chiuso."; }
        } else {
          esito.textContent = isWord
            ? "Non e' questa. Ricontrolla la somma delle nove risposte."
            : "Non torna. Rileggi l'aiuto 2 prima di riprovare.";
          focusForRetry(form, data.fields);
        }
      }).catch(function (reason) {
        // The answer was not judged, so clear any mark left by an earlier attempt.
        markFields(form, null);
        esito.textContent = reason === OFFLINE
          ? "Niente rete: la risposta non e' stata verificata. Riprova quando torni online."
          : "Errore del server: la risposta non e' stata controllata. Riprova fra poco.";
      });
    });
  });

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js").catch(function () { });
    });
  }
})();
