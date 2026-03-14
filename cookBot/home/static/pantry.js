// CSRF Token for AJAX requests
        function getCsrfToken() {
            // Try to get from meta tag first (Django sets this)
            const token = document.querySelector('[name=csrfmiddlewaretoken]');
            if (token) {
                return token.value;
            }
            // Fallback: get from cookie
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'csrftoken') {
                    return value;
                }
            }
            return '';
        }

        // Add Ingredient Function
        async function addIngredient() {
            const input = document.getElementById('ingredient-input');
            const ingredientName = input.value.trim();
            
            if (!ingredientName) {
                showMessage('Please enter an ingredient name', 'error');
                return;
            }

            try {
                const response = await fetch('/pantry/add/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                    },
                    body: JSON.stringify({
                        ingredient_name: ingredientName
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    // Add to DOM
                    addIngredientToDOM(data.ingredient);
                    input.value = '';
                    showMessage('Ingredient added successfully!', 'success');
                    searchRecipes(); // Refresh recipes
                } else {
                    showMessage(data.error || 'Failed to add ingredient', 'error');
                }
            } catch (error) {
                showMessage('Network error: ' + error.message, 'error');
            }
        }

        // Delete Ingredient Function
        async function deleteIngredient(ingredientId) {
            if (!confirm('Are you sure you want to remove this ingredient from your pantry?')) {
                return;
            }

            try {
                const response = await fetch(`/pantry/delete/${ingredientId}/`, {
                    method: 'POST',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                    }
                });

                if (response.ok) {
                    // Remove from DOM
                    const item = document.getElementById(`item-${ingredientId}`);
                    if (item) {
                        item.remove();
                    }
                    showMessage('Ingredient removed successfully!', 'success');
                    searchRecipes(); // Refresh recipes
                } else {
                    const errorData = await response.json();
                    showMessage(errorData.error || 'Failed to remove ingredient', 'error');
                }
            } catch (error) {
                showMessage('Network error: ' + error.message, 'error');
            }
        }

        // Add Ingredient to DOM
        function addIngredientToDOM(ingredient) {
            const pantryItems = document.getElementById('pantry-items');
            
            // Remove empty state if it exists
            const emptyState = pantryItems.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            const itemDiv = document.createElement('div');
            itemDiv.className = 'pantry-item';
            itemDiv.id = `item-${ingredient.id}`;
            itemDiv.innerHTML = `
                <span class="ingredient-name">` + ingredient.name.charAt(0).toUpperCase() + ingredient.name.slice(1) + `</span>
                <div class="ingredient-actions">
                    <button class="btn-nutrition nutrition-btn" data-ingredient="` + ingredient.name + `">Nutrition Info</button>
                    <button class="btn-remove" onclick="deleteIngredient(` + ingredient.id + `)">Remove</button>
                </div>
            `;
            
            pantryItems.appendChild(itemDiv);
        }

        // Search Recipes Function
        async function searchRecipes() {
            try {
                const response = await fetch('/pantry/search-recipes/', {
                    method: 'GET',
                    headers: {
                        'X-CSRFToken': getCsrfToken(),
                    }
                });

                const data = await response.json();

                if (response.ok) {
                    displayRecipes(data.recipes, data.api_status, data.message);
                } else {
                    showMessage(data.error || 'Failed to search recipes', 'error');
                }
            } catch (error) {
                showMessage('Network error: ' + error.message, 'error');
            }
        }

        // Display Recipes 
        function displayRecipes(recipes, apiStatus, message) {
            const recipesList = document.getElementById('recipes-list');
            
            // Clear existing content
            recipesList.innerHTML = '';
            
            // Show API status message if available
            if (message) {
                const statusDiv = document.createElement('div');
                statusDiv.className = 'recipe-status';
                statusDiv.innerHTML = `<p style="color: #666; font-style: italic; margin-bottom: 1rem;">${message}</p>`;
                recipesList.appendChild(statusDiv);
            }
            
            if (recipes.length === 0) {
                recipesList.innerHTML += '<div class="empty-state">No recipes found. Add more ingredients to your pantry!</div>';
                return;
            }

            recipes.forEach(recipe => {
                const recipeDiv = document.createElement('div');
                recipeDiv.className = 'recipe-card';
                
                const missedIngredients = recipe.missed_ingredients_string || 'None';
                const matchText = recipe.used_ingredient_count > 0 
                    ? `Uses ${recipe.used_ingredient_count} of your ingredients` 
                    : 'Generic recipe suggestion';
                
                // Add visual indicator for fallback recipes
                const fallbackIndicator = apiStatus === 'payment_required' 
                    ? '<span style="color: #888; font-size: 0.8rem; font-style: italic;">(Suggestion)</span>' 
                    : '';
                
                recipeDiv.innerHTML = `
                    <img src="${recipe.image}" alt="${recipe.title}" class="recipe-image">
                    <div class="recipe-info">
                        <h3>${recipe.title} ${fallbackIndicator}</h3>
                        <div class="recipe-matches">${matchText}</div>
                        <div class="recipe-missed">Missing: ${missedIngredients}</div>
                    </div>
                `;
                
                recipesList.appendChild(recipeDiv);
            });
        }

        // Message Display Function
        function showMessage(message, type) {
            const errorDiv = document.getElementById('error-message');
            const successDiv = document.getElementById('success-message');
            
            if (type === 'error') {
                errorDiv.textContent = message;
                errorDiv.style.display = 'block';
                successDiv.style.display = 'none';
            } else {
                successDiv.textContent = message;
                successDiv.style.display = 'block';
                errorDiv.style.display = 'none';
            }
            
            // Auto-hide messages after 3 seconds
            setTimeout(() => {
                errorDiv.style.display = 'none';
                successDiv.style.display = 'none';
            }, 3000);
        }

        // Enter key support for ingredient input
        document.getElementById('ingredient-input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                addIngredient();
            }
        });

        // Load initial recipes if pantry has items
        document.addEventListener('DOMContentLoaded', function() {
            const pantryItems = document.getElementById('pantry-items');
            if (pantryItems.children.length > 0 && !pantryItems.querySelector('.empty-state')) {
                searchRecipes();
            }
        });