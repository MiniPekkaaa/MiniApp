import React from 'react';
import { Button } from '@mui/material';

const Cart = () => {
  const handleCreateOrder = () => {
    const tg = window.Telegram.WebApp;
    const cartItems = JSON.parse(sessionStorage.getItem('cart') || '[]');
    
    if (cartItems.length === 0) {
      tg.showAlert('Корзина пуста');
      return;
    }

    fetch('/api/create-order', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        userId: tg.initDataUnsafe?.user?.id,
        items: cartItems
      })
    })
    .then(response => response.json())
    .then(data => {
      if (data.success) {
        sessionStorage.removeItem('cart');
        tg.showAlert('Заказ успешно создан!');
        window.location.href = '/';
      } else {
        tg.showAlert('Ошибка при создании заказа');
      }
    })
    .catch(() => {
      tg.showAlert('Ошибка при создании заказа');
    });
  };

  return (
    <div>
      <Button 
        variant="contained" 
        color="primary" 
        onClick={handleCreateOrder}
        fullWidth
        sx={{ mt: 2 }}
      >
        Оформить заказ
      </Button>
    </div>
  );
};

export default Cart; 