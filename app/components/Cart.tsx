import React, { useEffect, useState } from 'react';
import { Button } from '@mui/material';

interface BeerItem {
  _id: string;
  id: number;
  name: string;
  fullName: string;
  volume: number;
  price: number;
  legalEntity: number;
  quantity: number;
}

const Cart = () => {
  const [cartItems, setCartItems] = useState<BeerItem[]>([]);

  useEffect(() => {
    const items = localStorage.getItem('cart');
    if (items) {
      setCartItems(JSON.parse(items));
    }
  }, []);

  const handleCreateOrder = async () => {
    try {
      const tg = window.Telegram.WebApp;
      
      if (cartItems.length === 0) {
        tg.showAlert('Корзина пуста');
        return;
      }

      const response = await fetch('/api/create-order', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          userId: tg.initDataUnsafe?.user?.id,
          items: cartItems
        })
      });

      const result = await response.json();

      if (result.success) {
        localStorage.removeItem('cart');
        setCartItems([]);
        tg.showAlert('Заказ успешно создан!');
        tg.close();
      } else {
        throw new Error(result.error || 'Ошибка при создании заказа');
      }
    } catch (error) {
      console.error('Ошибка при создании заказа:', error);
      alert('Произошла ошибка при создании заказа: ' + error.message);
    }
  };

  const totalSum = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);

  return (
    <div style={{ padding: '20px' }}>
      {cartItems.map((item, index) => (
        <div key={index} style={{ 
          marginBottom: '10px', 
          padding: '10px', 
          backgroundColor: 'rgba(82, 136, 193, 0.1)',
          borderRadius: '8px'
        }}>
          <div>{item.name}</div>
          <div>Количество: {item.quantity}</div>
          <div>Цена: {item.price}₽</div>
          <div>Сумма: {item.price * item.quantity}₽</div>
        </div>
      ))}
      
      <div style={{ 
        marginTop: '20px', 
        marginBottom: '20px', 
        fontWeight: 'bold' 
      }}>
        Итого: {totalSum}₽
      </div>

      <Button 
        variant="contained" 
        onClick={handleCreateOrder}
        fullWidth
        sx={{ 
          mt: 2,
          backgroundColor: '#5288c1',
          '&:hover': {
            backgroundColor: '#4476ac'
          }
        }}
      >
        Оформить заказ
      </Button>
      
      <Button 
        variant="contained"
        onClick={() => window.Telegram.WebApp.close()}
        fullWidth
        sx={{ 
          mt: 2,
          backgroundColor: '#5288c1',
          '&:hover': {
            backgroundColor: '#4476ac'
          }
        }}
      >
        Назад
      </Button>
    </div>
  );
};

export default Cart; 