function addIngredient() {
    const container = document.getElementById('ingredients-container');
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = `
        <input type="number" name="ingredient_quantity[]" placeholder="Quantity" min="0.1" step="0.1" required>
        <select name="ingredient_unit[]">
            <option value=""></option>
            <option value="cup">cup</option>
            <option value="grams">grams</option>
            <option value="pounds">lb</option>
            <option value="table spoon">tbsp</option>
            <option value="tea spoon">tsp</option>
            <option value="ounces">oz</option>
        </select>
        <input type="text" name="ingredient_name[]" placeholder="Ingredient Name" required>
        <button type="button" onclick="removeRow(this)">Remove</button>
    `;
    container.appendChild(row);
}

function addStep() {
    const container = document.getElementById('steps-container');
    const row = document.createElement('div');
    row.className = 'step-row';
    row.innerHTML = `
        <textarea name="steps[]" placeholder="Step description" required></textarea>
        <button type="button" onclick="removeRow(this)">Remove</button>
    `;
    container.appendChild(row);
}

function removeRow(button) {
    button.parentElement.remove();
}
