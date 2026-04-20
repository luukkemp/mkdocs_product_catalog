function openCatalogModal(id) {
  var el = document.getElementById('catalog-overlay-' + id);
  if (el) {
    el.classList.add('active');
    document.body.style.overflow = 'hidden';
  }
}

function closeCatalogModal(id) {
  var el = document.getElementById('catalog-overlay-' + id);
  if (el) {
    el.classList.remove('active');
    document.body.style.overflow = '';
  }
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
      }, 100);
    }
  }
});

// Close all modals on Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.catalog-overlay.active').forEach(function(el) {
      el.classList.remove('active');
    });
    document.body.style.overflow = '';
  }
});
