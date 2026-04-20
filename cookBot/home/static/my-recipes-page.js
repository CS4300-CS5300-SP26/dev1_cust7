document.querySelectorAll('.recipe-bookmark-btn').forEach((button) => {
  let isLoading = false;

  button.addEventListener('click', () => {
    if (isLoading) return;
    isLoading = true;

    const toggleUrl = button.dataset.toggleUrl;
    const icon = button.querySelector('.icon');

    button.classList.add('loading');
    button.disabled = true;

    fetch(toggleUrl, {
      method: 'POST',
      headers: {
        'X-CSRFToken': getCookie('csrftoken'),
      },
    })
      .then(response => {
        if (!response.ok) {
          throw new Error(`Server error: ${response.status}`);
        }
        return response.json();
      })
      .then(data => {
        if (data.saved) {
          button.classList.add('saved');
          icon.innerHTML = '&#9733;';
          button.setAttribute('aria-label', 'Remove from saved recipes');
        } else {
          button.classList.remove('saved');
          icon.innerHTML = '&#9734;';
          button.setAttribute('aria-label', 'Save this recipe');
        }
      })
      .catch(error => {
        console.error('Error toggling bookmark:', error);
      })
      .finally(() => {
        button.classList.remove('loading');
        button.disabled = false;
        isLoading = false;
      });
  });
});
function getCookie(name) {

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

}