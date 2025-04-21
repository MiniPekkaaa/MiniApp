let tg = window.Telegram.WebApp;
let cart = {};
let selectedProduct = null;

// Инициализация Telegram WebApp
tg.ready();

// Функция для показа страницы выбора продукта
function showProductSelection() {
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('productSelection').style.display = 'block';
    document.getElementById('productsList').style.display = 'none';
    document.getElementById('quantitySelection').style.display = 'none';
}

// Функция для показа главного меню
function showMainMenu() {
    document.getElementById('mainMenu').style.display = 'block';
    document.getElementById('productSelection').style.display = 'none';
}

// Функция для переключения списка продуктов
function toggleProductList() {
    const productsList = document.getElementById('productsList');
    productsList.style.display = productsList.style.display === 'none' ? 'block' : 'none';
}

// Функция выбора продукта
function selectProduct(product) {
    selectedProduct = product;
    document.getElementById('selectedProduct').textContent = `${product.name} (${product.volume}л - ${product.price}₽)`;
    document.getElementById('productsList').style.display = 'none';
    document.getElementById('quantitySelection').style.display = 'block';
}

// Функция выбора количества
function selectQuantity(quantity) {
    if (selectedProduct) {
        addToCart(selectedProduct, quantity);
        showMainMenu();
    }
}

// Функция показа поля для ввода количества
function showCustomQuantity() {
    document.getElementById('customQuantity').style.display = 'flex';
}

// Функция применения пользовательского количества
function applyCustomQuantity() {
    const quantity = parseInt(document.getElementById('quantityInput').value);
    if (quantity && quantity >= 6) {
        selectQuantity(quantity);
    } else {
        tg.showAlert('Пожалуйста, введите число больше 5');
    }
}

// Функция добавления в корзину
function addToCart(product, quantity) {
    const productId = product.id;
    cart[productId] = (cart[productId] || 0) + quantity;
    updateCartCount();
    tg.showAlert(`Добавлено: ${product.name} - ${quantity}шт.`);
}

// Функция отмены заказа
function cancelOrder() {
    if (Object.keys(cart).length > 0) {
        tg.showConfirm('Вы уверены, что хотите отменить заказ?', function(confirmed) {
            if (confirmed) {
                cart = {};
                updateCartCount();
                tg.showAlert('Заказ отменен');
            }
        });
    } else {
        tg.showAlert('Корзина пуста');
    }
}

// Функция перехода в главное меню
function mainMenu() {
    tg.close();
}

// Функция обновления счетчика корзины
function updateCartCount() {
    const totalItems = Object.values(cart).reduce((a, b) => a + b, 0);
    document.getElementById('cartCount').textContent = totalItems;
}

// Обработчик для кнопки корзины
document.getElementById('cartButton').onclick = function() {
    if (Object.keys(cart).length === 0) {
        tg.showAlert('Корзина пуста');
        return;
    }

    let total = 0;
    let message = 'В корзине:\n\n';
    
    for (let productId in cart) {
        const quantity = cart[productId];
        const product = window.products.find(p => p.id === parseInt(productId));
        if (product) {
            const subtotal = product.price * quantity;
            message += `${product.name} × ${quantity} = ${subtotal} ₽\n`;
            total += subtotal;
        }
    }
    
    message += `\nИтого: ${total} ₽`;
    tg.showAlert(message);
};

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded');
    console.log('Products:', window.products);
});
