import React from 'react';
import { Button } from '@mui/material';
import { MongoClient, ObjectId } from 'mongodb';

const Cart = () => {
  const handleCreateOrder = async () => {
    try {
      const tg = window.Telegram.WebApp;
      const cartItems = JSON.parse(localStorage.getItem('cart') || '[]');
      
      if (cartItems.length === 0) {
        tg.showAlert('Корзина пуста');
        return;
      }

      const uri = 'mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true';
      const client = new MongoClient(uri);
      
      await client.connect();
      const db = client.db('Pivo');

      // Создаем уникальный идентификатор для заказа
      const orderId = new ObjectId();
      
      const orderData = {
        _id: orderId,
        status: "in work",
        userid: tg.initDataUnsafe?.user?.id?.toString() || "unknown",
        username: "ООО Пивной мир",
        process: "промежуточный процесс добавления пива",
        positions: Object.fromEntries(
          cartItems.map((item, index) => [
            `Position_${index + 1}`, {
              Beer_ID: Number(item.id),
              Beer_Name: item.name,
              Legal_Entity: 2,
              Beer_Count: Number(item.quantity)
            }
          ])
        )
      };

      console.log('Создаем заказ:', orderData);
      const result = await db.collection('Orders').insertOne(orderData);
      console.log('Результат создания заказа:', result);

      await client.close();

      // Очищаем корзину
      localStorage.removeItem('cart');
      tg.showAlert('Заказ успешно создан!');
      tg.close();
      
    } catch (error) {
      console.error('Ошибка при создании заказа:', error);
      alert('Произошла ошибка при создании заказа');
    }
  };

  return (
    <>
      <Button 
        variant="contained" 
        color="primary" 
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
    </>
  );
};

export default Cart; 