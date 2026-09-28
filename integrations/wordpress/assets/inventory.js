/**
 * Runs the PDF inventory scan in batches and shows progress.
 *
 * The progress bar updates on every batch; the status text (a live region) only
 * changes when the phase changes, so screen readers aren't flooded with updates.
 */
(function () {
  'use strict';

  var config = window.accesspdfInventory;
  var button = document.getElementById('accesspdf-scan');
  var status = document.getElementById('accesspdf-scan-status');
  var progress = document.getElementById('accesspdf-scan-progress');
  if (!config || !button || !status || !progress) {
    return;
  }

  var lastLabel = '';

  function show(data) {
    progress.max = Math.max(data.total, 1);
    progress.value = data.current;
    progress.setAttribute(
      'aria-valuetext',
      data.label + ': ' + data.current + ' ' + config.i18n.of + ' ' + data.total
    );
    if (data.label !== lastLabel) {
      lastLabel = data.label;
      status.textContent = data.label + '…';
    }
  }

  function step(phase, offset) {
    return window
      .fetch(config.restUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-WP-Nonce': config.nonce,
        },
        body: JSON.stringify({ phase: phase, offset: offset }),
      })
      .then(function (response) {
        return response.json().then(function (body) {
          if (!response.ok) {
            throw new Error(
              body && body.message ? body.message : 'HTTP ' + response.status
            );
          }
          return body;
        });
      })
      .then(function (data) {
        if (data.done) {
          status.textContent = config.i18n.done;
          window.location.reload();
          return null;
        }
        show(data);
        return step(data.phase, data.offset);
      });
  }

  button.addEventListener('click', function () {
    button.disabled = true;
    progress.hidden = false;
    status.textContent = config.i18n.starting;
    step('files', 0).catch(function (error) {
      status.textContent = config.i18n.failed + ' ' + error.message;
      button.disabled = false;
    });
  });
})();
