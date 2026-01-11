/* app/static/js/main.js */

document.addEventListener('DOMContentLoaded', () => {

    // --- 1. Theme Toggling Logic ---
    const themeToggleBtn = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    const icon = themeToggleBtn ? themeToggleBtn.querySelector('i') : null;

    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme');
    const systemPrefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    let currentTheme = savedTheme || (systemPrefersDark ? 'dark' : 'light');
    applyTheme(currentTheme, false); // Apply without animation on load

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            currentTheme = currentTheme === 'light' ? 'dark' : 'light';
            applyTheme(currentTheme, true); // Apply with animation on click
            localStorage.setItem('theme', currentTheme);

            // Add ripple effect
            createRipple(themeToggleBtn);
        });
    }

    function applyTheme(theme, animate = true) {
        // Add transition class for smooth theme change
        if (animate) {
            htmlElement.style.transition = 'background-color 0.3s ease, color 0.3s ease';
        }

        htmlElement.setAttribute('data-bs-theme', theme);

        if (icon) {
            if (theme === 'dark') {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            } else {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
        }

        // Remove transition after animation completes
        if (animate) {
            setTimeout(() => {
                htmlElement.style.transition = '';
            }, 300);
        }

        // Optional: Dispatch custom event for other scripts to react
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    // Create ripple effect on theme toggle
    function createRipple(button) {
        const ripple = document.createElement('span');
        const diameter = Math.max(button.clientWidth, button.clientHeight);
        const radius = diameter / 2;

        ripple.style.width = ripple.style.height = `${diameter}px`;
        ripple.style.left = '50%';
        ripple.style.top = '50%';
        ripple.style.transform = 'translate(-50%, -50%) scale(0)';
        ripple.style.position = 'absolute';
        ripple.style.borderRadius = '50%';
        ripple.style.backgroundColor = 'rgba(255, 255, 255, 0.6)';
        ripple.style.pointerEvents = 'none';
        ripple.style.animation = 'ripple-animation 0.6s ease-out';

        button.style.position = 'relative';
        button.style.overflow = 'hidden';
        button.appendChild(ripple);

        setTimeout(() => ripple.remove(), 600);
    }

    // Add ripple animation CSS dynamically
    if (!document.getElementById('ripple-styles')) {
        const style = document.createElement('style');
        style.id = 'ripple-styles';
        style.textContent = `
            @keyframes ripple-animation {
                to {
                    transform: translate(-50%, -50%) scale(2);
                    opacity: 0;
                }
            }
        `;
        document.head.appendChild(style);
    }

    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        if (!localStorage.getItem('theme')) {
            currentTheme = e.matches ? 'dark' : 'light';
            applyTheme(currentTheme, true);
        }
    });

    // --- 2. PWA Service Worker Registration ---
    // The URL is passed via data-attribute on body to avoid template tags in JS file
    const swUrl = document.body.getAttribute('data-sw-url');
    if ('serviceWorker' in navigator && swUrl) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register(swUrl)
                .then(registration => {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                })
                .catch(err => {
                    console.log('ServiceWorker registration failed: ', err);
                });
        });
    }

    // --- 3. Initialize Tooltips (Bootstrap 5) ---
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // --- 4. Product Gallery Switcher ---
    const mainImage = document.getElementById('mainProductImage');
    const thumbBtns = document.querySelectorAll('.gallery-thumb-btn');

    if (mainImage && thumbBtns.length > 0) {
        thumbBtns.forEach(btn => {
            btn.addEventListener('click', function () {
                // Remove active class from all
                thumbBtns.forEach(b => b.classList.remove('active'));
                // Add active to clicked
                this.classList.add('active');
                // Change main image source
                const newSrc = this.getAttribute('data-image-url');
                mainImage.style.opacity = '0.5';
                setTimeout(() => {
                    mainImage.src = newSrc;
                    mainImage.style.opacity = '1';
                }, 200);
            });
        });
    }

    // --- 5. Quantity Spinners (+/- buttons) ---
    // This creates a delegate listener for any quantity control on the page
    document.body.addEventListener('click', function (e) {
        if (e.target.closest('.quantity-btn')) {
            const btn = e.target.closest('.quantity-btn');
            const input = btn.parentElement.querySelector('.quantity-input');
            const type = btn.getAttribute('data-type'); // 'plus' or 'minus'

            if (input) {
                let val = parseInt(input.value) || 1;
                if (type === 'minus') {
                    val = val > 1 ? val - 1 : 1;
                } else {
                    val = val + 1;
                }
                input.value = val;

                // If this is an auto-submit form (like in cart), trigger change
                if (input.hasAttribute('onchange')) {
                    input.dispatchEvent(new Event('change'));
                }
            }
        }
    });

    // --- 6. Wishlist Logic (AJAX) ---
    const wishlistCounter = document.querySelector('.wishlist-count');

    document.body.addEventListener('click', function (e) {
        // Ищем кнопку или её родителя (если кликнули на иконку)
        const btn = e.target.closest('.btn-wishlist') || e.target.closest('.btn-wishlist-remove');

        if (!btn) return;

        // Предотвращаем переход по ссылке или отправку формы
        e.preventDefault();

        const productId = btn.getAttribute('data-product-id');
        const isRemoveBtn = btn.classList.contains('btn-wishlist-remove');

        fetch('/api/wishlist/toggle', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
            },
            body: JSON.stringify({ product_id: parseInt(productId) })
        })
            .then(response => {
                if (response.status === 401) {
                    // Если не авторизован, редирект на логин
                    window.location.href = '/auth/login';
                    return;
                }
                return response.json();
            })
            .then(data => {
                if (data && data.success) {
                    // 1. Если это страница Избранного и нажали крестик -> удаляем карточку
                    if (isRemoveBtn) {
                        const col = document.getElementById(`wishlist-item-${productId}`);
                        if (col) {
                            col.remove();
                            // Если товаров не осталось, перезагружаем, чтобы показать Empty State
                            const remaining = document.querySelectorAll('[id^="wishlist-item-"]');
                            if (remaining.length === 0) location.reload();
                        }
                    }
                    // 2. Если это Каталог или Товар -> меняем иконку
                    else {
                        const icon = btn.querySelector('i');
                        if (data.action === 'added') {
                            icon.classList.remove('far');
                            icon.classList.add('fas', 'text-danger');
                            // Анимация
                            icon.classList.add('animate__animated', 'animate__heartBeat');
                        } else {
                            icon.classList.remove('fas', 'text-danger', 'animate__animated', 'animate__heartBeat');
                            icon.classList.add('far');
                        }
                    }

                    // 3. Обновляем счетчик в шапке (простая логика: перезагружаем страницу или меняем число)
                    // Здесь реализуем изменение числа
                    if (wishlistCounter) {
                        let count = parseInt(wishlistCounter.innerText) || 0;
                        if (data.action === 'added') {
                            count++;
                        } else if (data.action === 'removed' && count > 0) {
                            count--;
                        }

                        if (count > 0) {
                            wishlistCounter.innerText = count;
                            wishlistCounter.classList.remove('d-none');
                        } else {
                            wishlistCounter.classList.add('d-none');
                        }
                    }
                }
            })
            .catch(error => console.error('Error:', error));
    });
});