// ===================================================================
// MEGAMART - ПЕРЕКЛЮЧЕНИЕ ТЕМЫ (Bootstrap 5.3+)
// Теперь использует data-bs-theme вместо кастомного класса
// ===================================================================

document.addEventListener('DOMContentLoaded', function() {
    const themeToggle = document.getElementById('theme-toggle');
    const themeIcon = document.getElementById('theme-icon');
    const htmlElement = document.documentElement; // <html> тег

    // Проверяем сохраненную тему в localStorage
    const savedTheme = localStorage.getItem('megamart-theme');
    
    // Если тема сохранена как 'dark', применяем её
    if (savedTheme === 'dark') {
        htmlElement.setAttribute('data-bs-theme', 'dark');
        themeIcon.className = 'fa-solid fa-sun'; // Иконка солнца для темной темы
    } else {
        htmlElement.setAttribute('data-bs-theme', 'light');
        themeIcon.className = 'fa-solid fa-moon'; // Иконка луны для светлой
    }

    // Обработчик клика
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            // Получаем текущую тему
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const isDark = currentTheme === 'dark';
            
            // Переключаем тему
            const newTheme = isDark ? 'light' : 'dark';
            htmlElement.setAttribute('data-bs-theme', newTheme);
            
            // Меняем иконку
            themeIcon.className = isDark ? 'fa-solid fa-moon' : 'fa-solid fa-sun';
            
            // Сохраняем выбор пользователя
            localStorage.setItem('megamart-theme', newTheme);
            
            console.log('Тема изменена на:', newTheme);
        });
    }
});