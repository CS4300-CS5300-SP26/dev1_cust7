function renumberSteps() {
    document.querySelectorAll('#steps-container .step-number').forEach((el, i) => {
      el.textContent = i + 1;
    });
  }
 
  function addIngredient() {
    const container = document.getElementById('ingredients-container');
    const row = container.querySelector('.ingredient-row').cloneNode(true);
    row.querySelectorAll('input').forEach(i => i.value = '');
    row.querySelector('select').selectedIndex = 0;
    container.appendChild(row);
  }
 
  function addStep() {
    const container = document.getElementById('steps-container');
    const row = container.querySelector('.step-row').cloneNode(true);
    row.querySelector('textarea').value = '';
    container.appendChild(row);
    renumberSteps();
  }
 
  function removeRow(btn) {
    const row = btn.closest('.ingredient-row, .step-row');
    const container = row.parentElement;
    if (container.children.length > 1) {
      row.remove();
      renumberSteps();
    }
  }