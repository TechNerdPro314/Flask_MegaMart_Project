class CartManager {
    constructor() {
        this.csrfToken = this.getCsrfToken();
        this.initEventListeners();
    }
    
    getCsrfToken() {
        return document.querySelector('meta[name="csrf-token"]')?.content || '';
    }
    
    initEventListeners() {
        // Добавление в корзину
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('add-to-cart-btn')) {
                e.preventDefault();
                const productId = e.target.dataset.productId;
                const quantity = parseInt(e.target.dataset.quantity || 1);
                this.addToCart(productId, quantity);
            }
        });
        
        // Обновление количества
        document.addEventListener('change', (e) => {
            if (e.target.classList.contains('cart-quantity-input')) {
                const productId = e.target.dataset.productId;
                const quantity = parseInt(e.target.value);
                this.updateCart(productId, quantity);
            }
        });
        
        // Удаление из корзины
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('remove-from-cart-btn')) {
                e.preventDefault();
                const productId = e.target.dataset.productId;
                this.removeFromCart(productId);
            }
        });
    }
    
    async addToCart(productId, quantity = 1) {
        try {
            const response = await fetch('/api/cart/add', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ product_id: productId, quantity: quantity })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.showNotification(data.message, 'success');
                this.updateCartCount(data.cart_count);
            } else {
                this.showNotification(data.error || 'Ошибка', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Произошла ошибка', 'danger');
        }
    }
    
    async updateCart(productId, quantity) {
        try {
            const response = await fetch('/api/cart/update', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ product_id: productId, quantity: quantity })
            });
            
            const data = await response.json();
            
            if (data.success) {
                this.updateTotalPrice(data.total_price);
                this.updateCartCount(data.cart_count);
            } else {
                this.showNotification(data.error || 'Ошибка', 'danger');
                location.reload();
            }
        } catch (error) {
            console.error('Error:', error);
            location.reload();
        }
    }
    
    async removeFromCart(productId) {
        if (!confirm('Удалить товар из корзины?')) return;
        
        try {
            const response = await fetch('/api/cart/remove', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({ product_id: productId })
            });
            
            const data = await response.json();
            
            if (data.success) {
                location.reload();
            } else {
                this.showNotification(data.error || 'Ошибка', 'danger');
            }
        } catch (error) {
            console.error('Error:', error);
            this.showNotification('Произошла ошибка', 'danger');
        }
    }
    
    updateCartCount(count) {
        const cartCountElements = document.querySelectorAll('.cart-count');
        cartCountElements.forEach(el => {
            el.textContent = count;
            el.style.display = count > 0 ? 'block' : 'none';
        });
    }
    
    updateTotalPrice(price) {
        const totalElements = document.querySelectorAll('.cart-total-price');
        totalElements.forEach(el => {
            el.textContent = `${price.toFixed(2)} ₽`;
        });
    }
    
    showNotification(message, type = 'info') {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
        alertDiv.style.zIndex = '1050';
        alertDiv.style.minWidth = '250px';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(alertDiv);
        
        setTimeout(() => {
            alertDiv.remove();
        }, 3000);
    }
}

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', () => {
    new CartManager();
});