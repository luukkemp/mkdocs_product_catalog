function openCatalogModal(id) {
  document.getElementById('catalog-overlay-' + id).classList.add('active');
  document.body.style.overflow = 'hidden';
}

function closeCatalogModal(id) {
  document.getElementById('catalog-overlay-' + id).classList.remove('active');
  document.body.style.overflow = '';
}

document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    document.querySelectorAll('.catalog-overlay.active').forEach(function(el) {
      el.classList.remove('active');
    });
    document.body.style.overflow = '';
  }
});
