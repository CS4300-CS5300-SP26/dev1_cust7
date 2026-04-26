document.addEventListener('DOMContentLoaded', function() {
    // Get API URLs from data attributes
    var apiEndpoints = document.getElementById('calendar-api-endpoints');
    var getMealsUrl = apiEndpoints.getAttribute('data-get-meals-url');
    var generateMealPlanUrl = apiEndpoints.getAttribute('data-generate-meal-plan-url');
    var saveMealPlanUrl = apiEndpoints.getAttribute('data-save-meal-plan-url');
    var calendarEl = document.getElementById('calendar');
    
    var calendar = new FullCalendar.Calendar(calendarEl, {
        initialView: 'dayGridMonth',
        headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek'
        },
        navLinks: true,
        editable: false,
        dayMaxEvents: true,
        height: 'auto',
        
        // Fetch events from our API
        events: function(info, successCallback, failureCallback) {
            fetch(getMealsUrl)
                .then(response => response.json())
                .then(data => {
                    // Transform API response to FullCalendar events
                    var events = data.meals.map(meal => {
                        // Add color class based on meal type
                        var classNames = [];
                        if (meal.meal_type === 'Breakfast') {
                            classNames.push('fc-event-breakfast');
                        } else if (meal.meal_type === 'Lunch') {
                            classNames.push('fc-event-lunch');
                        } else if (meal.meal_type === 'Dinner') {
                            classNames.push('fc-event-dinner');
                        }
                        
                        return {
                            id: meal.id,
                            title: meal.title,
                            start: meal.start,
                            classNames: classNames,
                            extendedProps: {
                                mealType: meal.meal_type,
                                recipeId: meal.recipe_id,
                                calories: meal.calories,
                                protein: meal.protein,
                                fat: meal.fat,
                                carbs: meal.carbs,
                            }
                        };
                    });
                    successCallback(events);
                })
                .catch(error => {
                    console.error('Error fetching meals:', error);
                    failureCallback(error);
                });
        },
        
        // Click on event to see details
        eventClick: function(info) {
            var props = info.event.extendedProps;
            var macros = '';

            if (props.calories || props.protein || props.fat || props.carbs) {
                macros = '\n\n── Macros ──'
                if (props.calories) macros += '\nCalories: ' + props.calories + ' kcal';
                if (props.protein)  macros += '\nProtein:  ' + props.protein + 'g';
                if (props.fat)      macros += '\nFat:      ' + props.fat + 'g';
                if (props.carbs)    macros += '\nCarbs:    ' + props.carbs + 'g';
            }
            alert('Meal: ' + info.event.title + '\nType: ' + props.mealType + macros);
        }
    });
    
    calendar.render();
    
    // Generate button click handler
    document.getElementById('generate-plan-btn').addEventListener('click', function() {
        var btn = this;
        var msgDiv = document.getElementById('generate-message');
        
        //Read user inputs
        var calories = document.getElementById('calories').value || null;
        var protein = document.getElementById('protein').value || null;
        var fat = document.getElementById('fat').value || null;
        var carbs = document.getElementById('carbs').value || null;
        var cuisine = document.getElementById('cuisine').value.trim() || null;
        var usePantry = document.getElementById('use-pantry').checked;

        // Disable button and show loading
        btn.disabled = true;
        btn.textContent = 'Generating...';
        msgDiv.textContent = '';
        
        fetch(generateMealPlanUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({
                calories: calories ? parseInt(calories) : null,
                protein: protein ? parseInt(protein) : null,
                fat: fat ? parseInt(fat) : null,
                carbs: carbs ? parseInt(carbs) : null,
                cuisine: cuisine,
                use_pantry: usePantry,
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                msgDiv.textContent = data.message;
                msgDiv.style.color = 'green';
                // Refresh calendar to show new meals
                calendar.refetchEvents();
            } else {
                msgDiv.textContent = data.error || 'Failed to generate meal plan';
                msgDiv.style.color = 'red';
            }
        })
        .catch(error => {
            msgDiv.textContent = 'Error: ' + error;
            msgDiv.style.color = 'red';
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = 'Generate Weekly Plan';
        });
    });
    
    // CSRF token helper function
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Save meal plan button click handler
    document.getElementById('save-meal-plan-btn').addEventListener('click', function() {
        var btn = this;
        var msgDiv = document.getElementById('save-meal-message');

        btn.disabled = true;
        btn.textContent = 'Saving...';
        msgDiv.textContent = '';
        msgDiv.style.color = '';

        fetch(saveMealPlanUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                msgDiv.textContent = data.message;
                msgDiv.style.color = 'green';
            } else {
                msgDiv.textContent = data.error || 'Failed to save meal plan.';
                msgDiv.style.color = 'red';
            }
        })
        .catch(error => {
            msgDiv.textContent = 'Error: ' + error;
            msgDiv.style.color = 'red';
        })
        .finally(() => {
            btn.disabled = false;
            btn.textContent = '📖 Save All Meals to My Recipes';
        });
    });
});