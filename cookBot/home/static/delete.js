function closeDeleteModal() {
  const modal = document.getElementById('delete-modal');
  const check = document.getElementById('delete-confirm-check');
  const btn = document.getElementById('delete-confirm-btn');

  modal.style.display = 'none';
  check.checked = false;
  btn.disabled = true;
}

const check = document.getElementById('delete-confirm-check');
const btn = document.getElementById('delete-confirm-btn');

if (check) {
  check.addEventListener('change', () => {
    btn.disabled = !check.checked;
  });
}
