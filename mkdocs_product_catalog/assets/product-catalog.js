function openCatalogModal(id) {
  var el = document.getElementById('catalog-overlay-' + id);
  if (el) {
    el.classList.add('active');
    document.body.style.overflow = 'hidden';
    history.pushState({ catalogModal: id }, '', '#modal-' + id);
    _expandNavForModal(id);
  }
}

// Expand all Material nav sections that contain a link to this modal so the
// services list stays visible in the sidebar while the modal is open.
function _expandNavForModal(id) {
  var link = document.querySelector('.md-nav a[href*="#modal-' + id + '"]');
  if (!link) return;
  link.classList.add('md-nav__link--active');
  // Walk up the DOM: for every md-nav element, check the toggle input that
  // controls it (Material uses a preceding <input type="checkbox"> sibling).
  var node = link.parentElement;
  while (node && node !== document.body) {
    if (node.tagName === 'NAV' && node.classList.contains('md-nav')) {
      var prev = node.previousElementSibling;
      while (prev) {
        if (prev.tagName === 'INPUT' && prev.type === 'checkbox') {
          prev.checked = true;
          break;
        }
        prev = prev.previousElementSibling;
      }
    }
    node = node.parentElement;
  }
}

function closeCatalogModal(id) {
  var el = document.getElementById('catalog-overlay-' + id);
  if (el) {
    el.classList.remove('active');
    document.body.style.overflow = '';
    // Only clear the hash if it still points to this modal
    if (window.location.hash === '#modal-' + id) {
      history.pushState({}, '', window.location.pathname + window.location.search);
    }
  }
}

function _closeAllModals() {
  document.querySelectorAll('.catalog-overlay.active').forEach(function(el) {
    el.classList.remove('active');
  });
  document.body.style.overflow = '';
}

// Copy current URL to clipboard and briefly show feedback on the share button
function copyCatalogLink(btn) {
  var url = window.location.href;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(url).then(function() {
      _flashCopied(btn);
    });
  } else {
    // Fallback for older browsers
    var ta = document.createElement('textarea');
    ta.value = url;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try { document.execCommand('copy'); } catch(e) {}
    document.body.removeChild(ta);
    _flashCopied(btn);
  }
}

function _flashCopied(btn) {
  var original = btn.getAttribute('aria-label');
  btn.setAttribute('aria-label', 'Copied!');
  btn.classList.add('catalog-modal-share--copied');
  setTimeout(function() {
    btn.setAttribute('aria-label', original);
    btn.classList.remove('catalog-modal-share--copied');
  }, 2000);
}

// Open modal from hash-based deep link, e.g. page.html#modal-{id}
window.addEventListener('DOMContentLoaded', function() {
  if (window.location.hash && window.location.hash.startsWith('#modal-')) {
    var modalId = window.location.hash.substring(7);
    var el = document.getElementById('catalog-overlay-' + modalId);
    if (el) {
      setTimeout(function() {
        el.classList.add('active');
        document.body.style.overflow = 'hidden';
        _expandNavForModal(modalId);
      }, 100);
    }
  }
});

// Handle browser back/forward: restore modal state from history
window.addEventListener('popstate', function(e) {
  _closeAllModals();
  if (e.state && e.state.catalogModal) {
    var el = document.getElementById('catalog-overlay-' + e.state.catalogModal);
    if (el) {
      el.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  } else if (window.location.hash && window.location.hash.startsWith('#modal-')) {
    var modalId = window.location.hash.substring(7);
    var el2 = document.getElementById('catalog-overlay-' + modalId);
    if (el2) {
      el2.classList.add('active');
      document.body.style.overflow = 'hidden';
    }
  }
});

// Close all modals on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var active = document.querySelector('.catalog-overlay.active');
    if (active) {
      var id = active.id.replace('catalog-overlay-', '');
      closeCatalogModal(id);
    }
  }
});
