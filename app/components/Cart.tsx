import React from 'react';
import { Button } from '@mui/material';
import { createOrder } from '../utils/mongodb';
import { getUserData } from '../utils/redis';

interface CartItem {
  id: number;
  name: string;
  quantity: number;
  legalEntity: number;
}

declare global {
  interface Window {
    Telegram: {
      WebApp: {
        initDataUnsafe?: {
          user?: {
            id?: number;
          };
        };
        showAlert: (message: string) => void;
      };
    };
  }
}

interface CartProps {
  cartItems: CartItem[];
  clearCart: () => void;
}

const Cart: React.FC<CartProps> = ({ cartItems, clearCart }) => {
  const handleCreateOrder = async () => {
    try {
      // Получаем Telegram WebApp из глобального объекта
      const tg = window.Telegram.WebApp;
      // Получаем ID пользователя из Telegram WebApp
      const userId = tg.initDataUnsafe?.user?.id?.toString();
      
      if (!userId) {
        throw new Error('Не удалось получить ID пользователя');
      }

      // Получаем данные пользователя из Redis
      const userData = await getUserData(userId);

      // Формируем позиции заказа
      const positions = cartItems.map((item: CartItem) => ({
        Beer_ID: item.id,
        Beer_Name: item.name,
        Legal_Entity: item.legalEntity,
        Beer_Count: item.quantity
      }));

      // Создаем заказ
      const orderData = {
        _id: new Date().getTime().toString(),
        status: "in work",
        userid: userId,
        username: userData.organization,
        process: "промежуточный процесс добавления пива",
        positions: positions
      };

      await createOrder(orderData);
      
      // Очищаем корзину и показываем сообщение об успехе
      clearCart();
      tg.showAlert('Заказ успешно создан!');
    } catch (error) {
      console.error('Error creating order:', error);
      alert('Ошибка при создании заказа');
    }
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