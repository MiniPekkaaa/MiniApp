import React from 'react';
import { Button } from '@mui/material';
import { MongoClient } from 'mongodb';

const Cart = () => {
  const handleCreateOrder = async () => {
    try {
      const tg = window.Telegram.WebApp;
      const cartItems = JSON.parse(sessionStorage.getItem('cart') || '[]');
      
      if (cartItems.length === 0) {
        tg.showAlert('Корзина пуста');
        return;
      }

      const uri = 'mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true';
      const client = new MongoClient(uri);
      
      await client.connect();
      const db = client.db('Pivo');
      
      const orderData = {
        _id: new Date().getTime().toString(),
        status: "in work",
        userid: tg.initDataUnsafe?.user?.id?.toString() || "unknown",
        username: "ООО Пивной мир",
        process: "промежуточный процесс добавления пива",
        positions: cartItems.map(item => ({
          Beer_ID: Number(item.id),
          Beer_Name: item.name,
          Legal_Entity: Number(item.legalEntity) || 2,
          Beer_Count: Number(item.quantity)
        }))
      };

      await db.collection('Orders').insertOne(orderData);
      await client.close();

      // Очищаем корзину
      sessionStorage.removeItem('cart');
      tg.showAlert('Заказ успешно создан!');
      window.location.href = '/';
      
    } catch (error) {
      console.error('Ошибка при создании заказа:', error);
      alert('Произошла ошибка при создании заказа');
    }
  };

  return (
    <Button 
      variant="contained" 
      color="primary" 
      onClick={handleCreateOrder}
      fullWidth
      sx={{ mt: 2 }}
    >
      Оформить заказ
    </Button>
  );
};

export default Cart; 