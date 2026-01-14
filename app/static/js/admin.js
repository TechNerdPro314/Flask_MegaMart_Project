// app/static/js/admin.js

// Переключение темы для админ панели
function toggleTheme() {
    const htmlElement = document.documentElement;
    const currentTheme = localStorage.getItem('adminTheme') || 'light';
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    if (newTheme === 'dark') {
        htmlElement.classList.add('admin-dark-theme');
        document.body.classList.add('admin-dark-theme');
    } else {
        htmlElement.classList.remove('admin-dark-theme');
        document.body.classList.remove('admin-dark-theme');
    }

    localStorage.setItem('adminTheme', newTheme);
    updateThemeIcon(newTheme);

    // Обновляем иконку в шапке, если она есть
    updateHeaderThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle i');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

function updateHeaderThemeIcon(theme) {
    const headerIcon = document.querySelector('#theme-toggle i');
    if (headerIcon) {
        headerIcon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// Загрузка темы при старте
document.addEventListener('DOMContentLoaded', function() {
    const savedTheme = localStorage.getItem('adminTheme') || 'light';
    const htmlElement = document.documentElement;

    if (savedTheme === 'dark') {
        htmlElement.classList.add('admin-dark-theme');
        document.body.classList.add('admin-dark-theme');
    }

    // Добавление кнопки переключения темы
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'theme-toggle';
    toggleBtn.innerHTML = `<i class="fas ${savedTheme === 'dark' ? 'fa-sun' : 'fa-moon'}"></i>`;
    toggleBtn.onclick = toggleTheme;
    toggleBtn.title = 'Переключить тему';
    document.body.appendChild(toggleBtn);

    // Инициализация боковой панели
    initializeSidebar();

    // Инициализация анимаций
    initializeAnimations();

    // Инициализация улучшенных элементов управления
    initializeEnhancedControls();
});

// Инициализация боковой панели
function initializeSidebar() {
    const sidebar = document.querySelector('.sidebar');
    const menuToggle = document.getElementById('menu-toggle');

    if (menuToggle) {
        menuToggle.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
        });
    }

    // Добавляем поддержку сворачивания боковой панели на десктопе
    const collapseBtn = document.createElement('button');
    collapseBtn.className = 'btn btn-sm btn-outline-secondary d-none d-lg-block';
    collapseBtn.id = 'sidebar-collapse';
    collapseBtn.innerHTML = '<i class="fas fa-chevron-left"></i>';
    collapseBtn.title = 'Свернуть боковую панель';
    collapseBtn.style.position = 'absolute';
    collapseBtn.style.right = '10px';
    collapseBtn.style.top = '10px';
    collapseBtn.style.zIndex = '1001';

    if (sidebar) {
        sidebar.style.position = 'relative';
        collapseBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            const icon = collapseBtn.querySelector('i');
            if (sidebar.classList.contains('collapsed')) {
                icon.className = 'fas fa-chevron-right';
            } else {
                icon.className = 'fas fa-chevron-left';
            }
        });

        // Добавляем кнопку сворачивания внутрь боковой панели
        sidebar.appendChild(collapseBtn);
    }
}

// Инициализация анимаций
function initializeAnimations() {
    // Анимации при загрузке элементов
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.1
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeInUp');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Применяем к элементам админ панели
    document.querySelectorAll('.card, .table, .form-control, .btn, .stat-card').forEach(el => {
        if (!el.classList.contains('animate__animated')) {
            el.classList.add('animate__animated', 'animate__fadeIn');
            observer.observe(el);
        }
    });
}

// Инициализация улучшенных элементов управления
function initializeEnhancedControls() {
    // Добавляем поддержку быстрого поиска
    addQuickSearch();

    // Добавляем поддержку массовых операций
    addBulkActions();

    // Добавляем улучшенные уведомления
    enhanceNotifications();

    // Добавляем поддержку автосохранения форм
    enableAutoSave();
}

// Добавляем быстрый поиск
function addQuickSearch() {
    const searchContainer = document.createElement('div');
    searchContainer.className = 'quick-search d-none d-lg-block';
    searchContainer.innerHTML = `
        <div class="input-group">
            <input type="text" class="form-control" placeholder="Поиск в админке...">
            <button class="btn btn-outline-secondary" type="button">
                <i class="fas fa-search"></i>
            </button>
        </div>
    `;

    const sidebarBrand = document.querySelector('.sidebar-brand');
    if (sidebarBrand) {
        sidebarBrand.parentNode.insertBefore(searchContainer, sidebarBrand.nextSibling);
    }
}

// Добавляем массовые операции
function addBulkActions() {
    // Добавляем чекбоксы для массовых операций к таблицам
    document.querySelectorAll('.table').forEach(table => {
        const headerRow = table.querySelector('thead tr');
        if (headerRow && !headerRow.querySelector('.bulk-select')) {
            const th = document.createElement('th');
            th.className = 'bulk-select';
            th.innerHTML = '<input type="checkbox" id="select-all">';
            headerRow.insertBefore(th, headerRow.firstChild);

            const firstBodyRow = table.querySelector('tbody tr');
            if (firstBodyRow) {
                const td = document.createElement('td');
                td.innerHTML = '<input type="checkbox" class="item-select">';
                firstBodyRow.insertBefore(td, firstBodyRow.firstChild);
            }
        }
    });

    // Обработчик "выбрать все"
    document.addEventListener('change', function(e) {
        if (e.target.id === 'select-all') {
            const isChecked = e.target.checked;
            document.querySelectorAll('.item-select').forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        }
    });
}

// Улучшаем уведомления
function enhanceNotifications() {
    // Добавляем возможность закрытия уведомлений через 5 секунд
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        if (!alert.querySelector('.close')) {
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'btn-close';
            closeBtn.setAttribute('data-bs-dismiss', 'alert');
            closeBtn.setAttribute('aria-label', 'Close');
            alert.appendChild(closeBtn);
        }

        // Автоматическое закрытие через 5 секунд для информационных сообщений
        if (alert.classList.contains('alert-info') || alert.classList.contains('alert-success')) {
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 5000);
        }
    });
}

// Включаем автосохранение форм
function enableAutoSave() {
    document.querySelectorAll('form').forEach(form => {
        if (form.querySelector('input[name="autosave"], textarea[name="autosave"]')) {
            const inputs = form.querySelectorAll('input, textarea, select');
            inputs.forEach(input => {
                input.addEventListener('input', debounce(autoSaveForm, 1000));
            });
        }
    });
}

// Функция для автосохранения формы
function autoSaveForm(event) {
    const form = event.target.closest('form');
    if (form && form.dataset.autosave !== 'false') {
        // Сохраняем данные формы в localStorage
        const formData = new FormData(form);
        const serializedData = new URLSearchParams(formData).toString();
        localStorage.setItem(`autosave_${form.id || form.name}`, serializedData);

        // Показываем уведомление
        showNotification('Черновик сохранен автоматически', 'info');
    }
}

// Функция для показа уведомлений
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.top = '20px';
    notification.style.right = '20px';
    notification.style.zIndex = '9999';
    notification.style.minWidth = '300px';
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    document.body.appendChild(notification);

    // Автоматически удаляем через 3 секунды
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 3000);
}

// Функция debounce для оптимизации вызовов
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Добавляем поддержку горячих клавиш
document.addEventListener('keydown', function(e) {
    // Ctrl+S для сохранения формы
    if (e.ctrlKey && e.key === 's') {
        e.preventDefault();
        const activeForm = document.activeElement.closest('form');
        if (activeForm) {
            const submitBtn = activeForm.querySelector('button[type="submit"], input[type="submit"]');
            if (submitBtn) {
                submitBtn.click();
            }
        }
    }

    // ESC для закрытия модальных окон
    if (e.key === 'Escape') {
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.hide();
            }
        });
    }
});

// Добавляем поддержку drag-and-drop для сортировки
function enableDragAndDrop() {
    const sortableTables = document.querySelectorAll('.sortable-table');
    sortableTables.forEach(table => {
        let draggedItem = null;

        table.querySelectorAll('tbody tr').forEach(row => {
            row.draggable = true;

            row.addEventListener('dragstart', function(e) {
                draggedItem = this;
                setTimeout(() => {
                    this.classList.add('opacity-50');
                }, 0);
            });

            row.addEventListener('dragend', function() {
                this.classList.remove('opacity-50');
                draggedItem = null;
            });

            row.addEventListener('dragover', function(e) {
                e.preventDefault();
            });

            row.addEventListener('drop', function(e) {
                e.preventDefault();
                if (draggedItem !== this) {
                    const allRows = Array.from(this.parentNode.children);
                    const draggedIndex = allRows.indexOf(draggedItem);
                    const targetIndex = allRows.indexOf(this);

                    if (draggedIndex < targetIndex) {
                        this.parentNode.insertBefore(draggedItem, this.nextSibling);
                    } else {
                        this.parentNode.insertBefore(draggedItem, this);
                    }

                    // Вызываем событие изменения порядка
                    this.dispatchEvent(new CustomEvent('row-reordered', {
                        detail: { draggedIndex, targetIndex }
                    }));
                }
            });
        });
    });
}

// Инициализация drag-and-drop при полной загрузке DOM
document.addEventListener('DOMContentLoaded', enableDragAndDrop);