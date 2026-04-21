// ── Helper: Get CSRF token from cookies ──
const getCookie = (name) => {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
};

// ── Render ingredients with Find Near Me buttons for missing ones ──
const ingredientsDataEl = document.getElementById('ingredients-data');
const pantryDataEl      = document.getElementById('pantry-data');
const list              = document.getElementById('ingredientsList');
 
if (ingredientsDataEl && pantryDataEl && list) {
  const ingredientsRaw = JSON.parse(ingredientsDataEl.textContent);
  const pantryNames    = new Set(JSON.parse(pantryDataEl.textContent));
 
  ingredientsRaw.forEach(ing => {
    const li       = document.createElement('li');
    const inPantry = pantryNames.has(ing.name.toLowerCase());
 
    if (inPantry) {
      li.textContent = ing.display;
    } else {
      const nameSpan = document.createElement('span');
      nameSpan.className   = 'missing-ingredient';
      nameSpan.textContent = ing.display;
 
      const btn = document.createElement('button');
      btn.className          = 'find-near-me-btn';
      btn.textContent        = '📍 Find Near Me';
      btn.dataset.ingredient = ing.name;
      btn.addEventListener('click', () => findNearMe(ing.name));
 
      li.appendChild(nameSpan);
      li.appendChild(btn);
    }
 
    list.appendChild(li);
  });
}
 
// ── Kroger store finder ──
function findNearMe(ingredientName) {
  const panel     = document.getElementById('krogerPanel');
  const results   = document.getElementById('krogerResults');
  const titleIngr = document.getElementById('krogerIngredientName');
 
  titleIngr.textContent = ingredientName;
  results.innerHTML     = '<p class="kroger-loading">Getting your location&#8230;</p>';
  panel.style.display   = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
 
  if (!navigator.geolocation) {
    results.innerHTML = '<p class="kroger-error">Geolocation is not supported by your browser.</p>';
    return;
  }
 
  navigator.geolocation.getCurrentPosition(
    position => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;
 
      results.innerHTML = '<p class="kroger-loading">Searching for nearby stores&#8230;</p>';
 
      fetch(`/kroger/stores/?lat=${lat}&lon=${lon}&ingredient=${encodeURIComponent(ingredientName)}`)
        .then(res => res.json())
        .then(data => {
          if (data.error) {
            results.innerHTML = `<p class="kroger-error">Error: ${data.error}</p>`;
            return;
          }
          if (!data.stores || data.stores.length === 0) {
            results.innerHTML = '<p class="kroger-empty">No Kroger-family stores found within 10 miles.</p>';
            return;
          }
          results.innerHTML = data.stores.map(store => `
            <div class="store-card">
              <div class="store-name">${store.name}</div>
              <div class="store-address">${store.address}, ${store.city}, ${store.state} ${store.zip}</div>
              ${store.distance !== '' ? `<span class="store-distance">${parseFloat(store.distance).toFixed(1)} mi away</span>` : ''}
            </div>
          `).join('');
        })
        .catch(() => {
          results.innerHTML = '<p class="kroger-error">Failed to reach the store finder. Please try again.</p>';
        });
    },
    () => {
      results.innerHTML = '<p class="kroger-error">Location access was denied. Please allow location access and try again.</p>';
    }
  );
}
 
// ── Close panel ──
const closeBtn = document.getElementById('krogerCloseBtn');
if (closeBtn) {
  closeBtn.addEventListener('click', () => {
    document.getElementById('krogerPanel').style.display = 'none';
  });
}

// ── Bookmark Toggle ──
const bookmarkBtn = document.getElementById('bookmarkBtn');
if (bookmarkBtn) {
  let isLoading = false;
  
  bookmarkBtn.addEventListener('click', () => {
    if (isLoading) return;
    isLoading = true;
    
    const toggleUrl = bookmarkBtn.dataset.toggleUrl;
    const icon = bookmarkBtn.querySelector('.icon');
    
    // Add loading state
    bookmarkBtn.classList.add('loading');
    bookmarkBtn.disabled = true;

    fetch(toggleUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
        'Content-Type': 'application/json',
      },
    })
    .then(response => {
      if (!response.ok) {
        if (response.status === 403 || response.redirected) {
          throw new Error('Session expired. Please sign in again.');
        }
        throw new Error(`Server error: ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.saved) {
        bookmarkBtn.classList.add('saved');
        icon.innerHTML = '&#9733;'; // Filled star
        bookmarkBtn.setAttribute('aria-label', 'Remove from saved recipes');
      } else {
        bookmarkBtn.classList.remove('saved');
        icon.innerHTML = '&#9734;'; // Empty star
        bookmarkBtn.setAttribute('aria-label', 'Save this recipe');
      }
    })
    .catch(error => {
      console.error('Error toggling bookmark:', error);
      alert(error.message);
    })
    .finally(() => {
      bookmarkBtn.classList.remove('loading');
      bookmarkBtn.disabled = false;
      isLoading = false;
    });
  });
}

// Reply form toggle functionality
document.addEventListener('DOMContentLoaded', function() {
  // Handle Reply button clicks
  document.addEventListener('click', function(e) {
    if (e.target.classList.contains('reply-btn')) {
      const commentId = e.target.dataset.commentId;
      const replyForm = document.getElementById(`reply-form-${commentId}`);
      
      // Toggle visibility
      if (replyForm.style.display === 'none') {
        replyForm.style.display = 'block';
        replyForm.querySelector('textarea').focus();
      } else {
        replyForm.style.display = 'none';
      }
    }

    // Handle Cancel button clicks
    if (e.target.classList.contains('reply-cancel-btn')) {
      const formContainer = e.target.closest('.reply-form-container');
      formContainer.style.display = 'none';
    }
  });
});
