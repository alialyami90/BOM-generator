/* Entry point. */
(function () {
  if (!location.hash) location.hash = '#/home';
  document.querySelector('.skip').addEventListener('click', (e) => { e.preventDefault(); document.getElementById('main').focus(); });
  App.render();
})();
