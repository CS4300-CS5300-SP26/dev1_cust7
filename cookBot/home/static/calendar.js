document.addEventListener('DOMContentLoaded', function() {
    // Get API URLs from data attributes
    var apiEndpoints = document.getElementById('calendar-api-endpoints');
    var getMealsUrl = apiEndpoints.getAttribute('data-get-meals-url');
    var generateMealPlanUrl = apiEndpoints.getAttribute('data-generate-meal-plan-url');
    
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
                                recipeId: meal.recipe_id
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
            var mealType = info.event.extendedProps.mealType;
            alert('Meal: ' + info.event.title + '\nType: ' + mealType);
        }
    });
    
    calendar.render();
    
    // Generate button click handler
    document.getElementById('generate-plan-btn').addEventListener('click', function() {
        var btn = this;
        var msgDiv = document.getElementById('generate-message');
        
        // Disable button and show loading
        btn.disabled = true;
        btn.textContent = 'Generating...';
        msgDiv.textContent = '';
        
        fetch(generateMealPlanUrl, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken')
            }
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
});