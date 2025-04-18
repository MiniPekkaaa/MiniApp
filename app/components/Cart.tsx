import { Button } from '@mui/material';
import { createOrder } from '../utils/mongodb';

const handleCreateOrder = async () => {
  try {
    const orderData = {
      _id: new Date().getTime().toString(),
      status: "in work",
      userid: "7944903241", // Здесь нужно использовать реальный ID пользователя
      username: "ООО Пивной мир",
      process: "промежуточный процесс добавления пива",
      positions: cartItems.map(item => ({
        Beer_ID: item.id,
        Beer_Name: item.name,
        Legal_Entity: 2, // Предполагаемое значение
        Beer_Count: item.quantity
      }))
    };

    await createOrder(orderData);
    // Очистить корзину и показать сообщение об успехе
    clearCart();
    alert('Заказ успешно создан!');
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