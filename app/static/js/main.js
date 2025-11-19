document.addEventListener('DOMContentLoaded', () => {
    // --- Переключатель темы ---
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const currentTheme = localStorage.getItem('theme') || 'light';

    document.documentElement.setAttribute('data-bs-theme', currentTheme);
    if (currentTheme === 'dark') {
        if (themeIcon) {
            themeIcon.classList.remove('fa-moon');
            themeIcon.classList.add('fa-sun');
        }
    }

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            let theme = document.documentElement.getAttribute('data-bs-theme');
            if (theme === 'light') {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeIcon.classList.remove('fa-moon');
                themeIcon.classList.add('fa-sun');
            } else {
                document.documentElement.setAttribute('data-bs-theme', 'light');
                localStorage.setItem('theme', 'light');
                themeIcon.classList.remove('fa-sun');
                themeIcon.classList.add('fa-moon');
            }
        });
    }

    // --- Логика для списка желаний ---
    document.querySelectorAll('.wishlist-toggle-btn').forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            const productId = this.dataset.productId;
            const icon = this.querySelector('i');
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');

            fetch('/api/wishlist/toggle', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ product_id: parseInt(productId) })
            })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        if (data.action === 'added') {
                            icon.classList.remove('fa-regular');
                            icon.classList.add('fa-solid', 'text-danger');
                        } else {
                            icon.classList.remove('fa-solid', 'text-danger');
                            icon.classList.add('fa-regular');
                        }
                    }
                })
                .catch(error => console.error('Error:', error));
        });
    });

    // --- Логика автодополнения ---
    const searchInput = document.getElementById('search-input');
    const suggestionsContainer = document.getElementById('autocomplete-container');
    const searchForm = document.getElementById('search-form');

    if (searchInput && suggestionsContainer && searchForm) {
        searchInput.addEventListener('input', function (e) {
            const query = e.target.value;
            if (query.length < 2) {
                suggestionsContainer.innerHTML = '';
                return;
            }

            fetch(`/api/search/autocomplete?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    suggestionsContainer.innerHTML = '';
                    if (data.length > 0) {
                        const suggestionsList = document.createElement('div');
                        suggestionsList.className = 'list-group position-absolute top-100 start-0 w-100';
                        suggestionsList.style.zIndex = '1050';

                        data.forEach(item => {
                            const suggestionItem = document.createElement('a');
                            suggestionItem.href = item.url;
                            suggestionItem.className = 'list-group-item list-group-item-action';
                            suggestionItem.textContent = item.name;
                            suggestionsList.appendChild(suggestionItem);
                        });
                        suggestionsContainer.appendChild(suggestionsList);
                    }
                });
        });

        document.addEventListener('click', function (e) {
            if (!searchForm.contains(e.target)) {
                suggestionsContainer.innerHTML = '';
            }
        });
    }

    // --- Регистрация сервис-воркера для PWA ---
    if ('serviceWorker' in navigator) {
        const swUrl = document.body.dataset.swUrl;
        if (swUrl) {
            window.addEventListener('load', () => {
                navigator.serviceWorker.register(swUrl)
                    .then(reg => console.log('Service worker registered.', reg))
                    .catch(err => console.log('Service worker registration failed: ', err));
            });
        }
    }
});