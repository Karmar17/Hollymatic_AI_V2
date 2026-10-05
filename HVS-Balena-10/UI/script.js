(function () {
  var tabs = [document.getElementById('tab-zoho'), document.getElementById('tab-chat')];
  var panels = [document.getElementById('panel-zoho'), document.getElementById('panel-chat')];

  function activate(index) {
    tabs.forEach(function (t, i) {
      var selected = i === index;
      t.setAttribute('aria-selected', String(selected));
      t.tabIndex = selected ? 0 : -1;
      panels[i].classList.toggle('active', selected);
    });
    tabs[index].focus();
  }

  tabs.forEach(function (tab, i) {
    tab.addEventListener('click', function () { activate(i); });
    tab.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        var next = e.key === 'ArrowRight' ? (i + 1) % tabs.length : (i - 1 + tabs.length) % tabs.length;
        activate(next);
      }
    });
  });
})();
