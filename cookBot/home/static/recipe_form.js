function addIngredient() {
    const container = document.getElementById('ingredients-container');
    const row = document.createElement('div');
    row.className = 'ingredient-row';
    row.innerHTML = `
        <input type="number" name="ingredient_quantity[]" placeholder="Quantity" min="0.001" step="0.0001" required>
        <select name="ingredient_unit[]">
            <option value=""></option>
            <option value="cups">cup</option>
            <option value="grams">g</option>
            <option value="lbs">lb</option>
            <option value="tablespoons">tbsp</option>
            <option value="teaspoons">tsp</option>
            <option value="ozs">oz</option>
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
