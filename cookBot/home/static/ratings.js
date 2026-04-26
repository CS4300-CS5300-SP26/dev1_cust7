(function () {
    const widget = document.getElementById('starRatingWidget');
    if (!widget) return;
  
    const buttons        = widget.querySelectorAll('.star-btn');
    const avgEl          = document.getElementById('avgDisplay');
    const starPrompt     = document.getElementById('starPrompt');
    const rateUrl        = widget.dataset.rateUrl;
    const csrfToken      = widget.dataset.csrfToken;
    const isAuthenticated = widget.dataset.authenticated === 'true';
  
    if (isAuthenticated) {
      // Hover preview
      buttons.forEach(btn => {
        btn.addEventListener('mouseenter', () => {
          const val = parseInt(btn.dataset.value);
          buttons.forEach(b => {
            b.classList.toggle('hover', parseInt(b.dataset.value) <= val);
          });
        });
        btn.addEventListener('mouseleave', () => {
          buttons.forEach(b => b.classList.remove('hover'));
        });
      });
  
      // Submit rating
      buttons.forEach(btn => {
        btn.addEventListener('click', () => {
          const stars = parseInt(btn.dataset.value);
  
          fetch(rateUrl, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken,
            },
            body: JSON.stringify({ stars }),
          })
          .then(res => {
            if (!res.ok) {
              throw new Error(`Server returned ${res.status}`);
            }
            return res.json();
          })
          .then(data => {
            if (data.success) {
              buttons.forEach(b => {
                b.classList.toggle('filled', parseInt(b.dataset.value) <= data.stars);
              });
              avgEl.textContent = data.average + ' / 5';
              const countEl = widget.querySelector('.star-count');
              if (countEl) {
                countEl.textContent = `(${data.count} rating${data.count !== 1 ? 's' : ''})`;
                countEl.style.display = '';  // unhide if it was hidden (first ever rating)
              }
              if (starPrompt) {
                starPrompt.textContent = `Your rating: ${data.stars} star${data.stars !== 1 ? 's' : ''} — click to change`;
              }
            }
          })
          .catch(err => {
            if (starPrompt) starPrompt.textContent = 'Something went wrong, please try again.';
            console.error('Rating error:', err.message);
          });
        });
      });
    }
  
    window.addEventListener('pageshow', function (event) {
      if (event.persisted) {
        window.location.reload();
      }
    });
  })();