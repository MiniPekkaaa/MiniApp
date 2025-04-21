let tg = window.Telegram.WebApp;
let cart = {};
let selectedProduct = null;

// Инициализация Telegram WebApp
tg.ready();
tg.expand();

// Проверка авторизации при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    checkAuthorization();
});

// Функция проверки авторизации
function checkAuthorization() {
    const userId = tg.initDataUnsafe?.user?.id;
    if (!userId) {
        showRegistration();
        return;
    }

    fetch(`/api/check-auth/${userId}`)
        .then(response => response.json())
        .then(data => {
            if (data.isAuthorized) {
                showMainMenu();
            } else {
                showRegistration();
            }
        })
        .catch(error => {
            console.error('Ошибка при проверке авторизации:', error);
            showRegistration();
        });
}

// Функции для навигации между страницами
function showRegistration() {
    document.getElementById('registration').style.display = 'block';
    document.getElementById('main_menu').style.display = 'none';
    document.getElementById('order_type').style.display = 'none';
    document.getElementById('manual_input').style.display = 'none';
}

function showMainMenu() {
    document.getElementById('registration').style.display = 'none';
    document.getElementById('main_menu').style.display = 'block';
    document.getElementById('order_type').style.display = 'none';
    document.getElementById('manual_input').style.display = 'none';
}

function showOrderType() {
    document.getElementById('registration').style.display = 'none';
    document.getElementById('main_menu').style.display = 'none';
    document.getElementById('order_type').style.display = 'block';
    document.getElementById('manual_input').style.display = 'none';
}

function showManualInput() {
    document.getElementById('registration').style.display = 'none';
    document.getElementById('main_menu').style.display = 'none';
    document.getElementById('order_type').style.display = 'none';
    document.getElementById('manual_input').style.display = 'block';
}

// Функция для показа страницы выбора продукта
function showProductSelection() {
    document.getElementById('mainMenu').style.display = 'none';
    document.getElementById('productSelection').style.display = 'block';
    document.getElementById('productsList').style.display = 'none';
    document.getElementById('quantitySelection').style.display = 'none';
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

// Обработчики кнопок главного меню
function handleNewOrder() {
    showOrderType();
}

function handleMyOrders() {
    tg.showAlert('Функция в разработке');
}

// Обработчики кнопок страницы выбора типа заказа
function handleRemainingInput() {
    tg.showAlert('Функция в разработке');
}

function handleManualInput() {
    showManualInput();
}

// Функции для работы с количеством
function incrementQuantity() {
    let quantityInput = document.getElementById('quantity');
    quantityInput.value = parseInt(quantityInput.value) + 1;
}

function decrementQuantity() {
    let quantityInput = document.getElementById('quantity');
    if (parseInt(quantityInput.value) > 1) {
        quantityInput.value = parseInt(quantityInput.value) - 1;
    }
}

// Функция добавления в корзину
function addToCart() {
    const productSelect = document.getElementById('product_select');
    const quantityInput = document.getElementById('quantity');
    
    if (!productSelect.value) {
        tg.showAlert('Выберите товар');
        return;
    }

    const selectedOption = productSelect.selectedOptions[0];
    const product = {
        id: parseInt(productSelect.value),
        name: selectedOption.dataset.name,
        fullName: selectedOption.dataset.fullname,
        volume: parseFloat(selectedOption.dataset.volume),
        price: parseFloat(selectedOption.dataset.price),
        legalEntity: parseInt(selectedOption.dataset.legalEntity),
        quantity: parseInt(quantityInput.value)
    };

    try {
        const existingCart = JSON.parse(localStorage.getItem('cart') || '[]');
        const updatedCart = [...existingCart, product];
        localStorage.setItem('cart', JSON.stringify(updatedCart));
        tg.showAlert('Товар добавлен в корзину');
        productSelect.value = '';
        quantityInput.value = '1';
    } catch (error) {
        console.error('Ошибка при добавлении в корзину:', error);
        tg.showAlert('Ошибка при добавлении в корзину');
    }
}
