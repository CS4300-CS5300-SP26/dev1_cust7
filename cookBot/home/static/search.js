document.addEventListener("DOMContentLoaded", () => {
    // ── Auto-submit form when any tag checkbox is toggled ──
    document.querySelectorAll('.tag-chip input[type="checkbox"]').forEach(checkbox => {
      checkbox.addEventListener('change', () => {
        checkbox.closest('form').submit();
      });
    });
  
    // ── Collapsible filter toggle ──
    const toggle = document.getElementById('filterToggle');
    const content = document.getElementById('filterContent');
    const icon = document.getElementById('filterIcon');
  
    if (toggle && content && icon) {
      toggle.addEventListener('click', () => {
        content.classList.toggle('collapsed');
        icon.classList.toggle('rotated');
      });
    }
  
    // ── Auto-collapse if no filters selected ──
    if (content) {
      const hasFilters = false;
  
      if (!hasFilters) {
        content.classList.add('collapsed');
      }
    }
  });
