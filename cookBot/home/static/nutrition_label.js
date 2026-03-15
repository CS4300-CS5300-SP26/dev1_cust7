(function () {
  const overlay  = document.getElementById('nutrition-overlay');
  const loading  = document.getElementById('nutrition-loading');
  const errorEl  = document.getElementById('nutrition-error');
  const errorMsg = document.getElementById('nutrition-error-msg');
  const content  = document.getElementById('nutrition-content');

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.nutrition-btn');
    if (!btn) return;
    const name = btn.dataset.ingredient;
    if (name) openModal(name);
  });

  document.getElementById('nutrition-close-btn').addEventListener('click', closeModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  function openModal(name) {
    setState('loading');
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
    fetchNutrition(name);
  }

  function closeModal() {
    overlay.classList.remove('active');
    document.body.style.overflow = '';
  }

  function setState(state) {
    loading.style.display = state === 'loading' ? 'flex'  : 'none';
    errorEl.style.display = state === 'error'   ? 'block' : 'none';
    content.style.display = state === 'content' ? 'block' : 'none';
  }

  async function fetchNutrition(name) {
    try {
      const res = await fetch(`/nutrition/${encodeURIComponent(name)}/`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      populateLabel(data);
      setState('content');
    } catch (err) {
      errorMsg.textContent = `Could not load nutrition info for "${name}".`;
      setState('error');
    }
  }

  function get(nutrients, name) {
    return nutrients.find(n => n.name === name) || null;
  }

  function fmt(n) {
    if (!n) return '—';
    const v = parseFloat(n.amount);
    return `${Number.isInteger(v) ? v : v.toFixed(1)}${n.unit}`;
  }

  function dv(n) {
    return (n && n.percentOfDailyNeeds != null) ? `${Math.round(n.percentOfDailyNeeds)}%` : '—%';
  }

  function set(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function populateLabel(data) {
    const nutrients = data.nutrition?.nutrients || [];
    const wps = data.nutrition?.weightPerServing;
    set('fda-serving-size', wps ? `${wps.amount}${wps.unit}` : '1 serving');

    const cal = get(nutrients, 'Calories');
    set('fda-calories', cal ? Math.round(cal.amount) : '—');

    const fat      = get(nutrients, 'Fat');
    const satFat   = get(nutrients, 'Saturated Fat');
    const transFat = get(nutrients, 'Trans Fat');
    set('fda-fat',       fmt(fat));      set('fda-fat-dv',       dv(fat));
    set('fda-sat-fat',   fmt(satFat));   set('fda-sat-fat-dv',   dv(satFat));
    set('fda-trans-fat', fmt(transFat));

    const chol   = get(nutrients, 'Cholesterol');
    const sodium = get(nutrients, 'Sodium');
    set('fda-cholesterol', fmt(chol));   set('fda-cholesterol-dv', dv(chol));
    set('fda-sodium',      fmt(sodium)); set('fda-sodium-dv',      dv(sodium));

    const carbs = get(nutrients, 'Carbohydrates');
    const fiber = get(nutrients, 'Fiber');
    const sugar = get(nutrients, 'Sugar');
    set('fda-carbs', fmt(carbs)); set('fda-carbs-dv', dv(carbs));
    set('fda-fiber', fmt(fiber)); set('fda-fiber-dv', dv(fiber));
    set('fda-sugar', fmt(sugar));

    const protein = get(nutrients, 'Protein');
    set('fda-protein', fmt(protein)); set('fda-protein-dv', dv(protein));

    set('fda-vitd',      dv(get(nutrients, 'Vitamin D')));
    set('fda-calcium',   dv(get(nutrients, 'Calcium')));
    set('fda-iron',      dv(get(nutrients, 'Iron')));
    set('fda-potassium', dv(get(nutrients, 'Potassium')));
    set('fda-vita',      dv(get(nutrients, 'Vitamin A')));
    set('fda-vitc',      dv(get(nutrients, 'Vitamin C')));
  }
})();