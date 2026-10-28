/* Entry point. */
(function () {
  if (!location.hash) location.hash = '#/home';
  document.querySelector('.skip').addEventListener('click', (e) => { e.preventDefault(); document.getElementById('main').focus(); });
  App.render();
  Bridge.call('app_info').then(App.setAppInfo).catch((err) => {
    if (err.kind !== 'no_backend') App.toast(`Could not read the app's state: ${err.message}`, 'error');
  });
})();
