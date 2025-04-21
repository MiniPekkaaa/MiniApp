import React, { useEffect, useState } from 'react';
import { Button, Container, Typography, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const MainMenu = () => {
  const navigate = useNavigate();
  const [isAuthorized, setIsAuthorized] = useState(false);
  const tg = window.Telegram.WebApp;

  useEffect(() => {
    // Проверка авторизации пользователя
    const checkAuth = async () => {
      try {
        const userId = tg.initDataUnsafe?.user?.id;
        if (!userId) {
          tg.showAlert('Необходимаа авторизация в Telegram');
          return;
        }

        const response = await fetch(`/api/check-auth/${userId}`);
        const data = await response.json();
        setIsAuthorized(data.isAuthorized);

        if (!data.isAuthorized) {
          tg.showAlert('Пожалуйста, зарегистрируйтесь в системе');
        }
      } catch (error) {
        console.error('Ошибка при проверке авторизации:', error);
        tg.showAlert('Ошибка при проверке авторизации');
      }
    };

    checkAuth();
  }, []);

  const handleNewOrder = () => {
    if (!isAuthorized) {
      tg.showAlert('Необходима регистрация в системе');
      return;
    }
    navigate('/order-type');
  };

  const handleMyOrders = () => {
    if (!isAuthorized) {
      tg.showAlert('Необходима регистрация в системе');
      return;
    }
    navigate('/my-orders');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h5" component="h1" align="center">
          Главное меню
        </Typography>
        <Button
          variant="contained"
          fullWidth
          onClick={handleNewOrder}
          disabled={!isAuthorized}
        >
          Новый заказ
        </Button>
        <Button
          variant="contained"
          fullWidth
          onClick={handleMyOrders}
          disabled={!isAuthorized}
        >
          Мои заказы
        </Button>
      </Box>
    </Container>
  );
};

export default MainMenu; 