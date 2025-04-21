import React from 'react';
import { Button, Container, Typography, Box } from '@mui/material';
import { useNavigate } from 'react-router-dom';

const OrderType = () => {
  const navigate = useNavigate();
  const tg = window.Telegram.WebApp;

  const handleManualOrder = () => {
    navigate('/manual-order');
  };

  const handleRemainingOrder = () => {
    navigate('/remaining-order');
  };

  const handleMainMenu = () => {
    navigate('/');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h5" component="h1" align="center">
          Выберите тип заказа
        </Typography>
        <Button
          variant="contained"
          fullWidth
          onClick={handleRemainingOrder}
        >
          Ввести остатки
        </Button>
        <Button
          variant="contained"
          fullWidth
          onClick={handleManualOrder}
        >
          Добавить позиции вручную
        </Button>
        <Button
          variant="outlined"
          fullWidth
          onClick={handleMainMenu}
        >
          Главное меню
        </Button>
      </Box>
    </Container>
  );
};

export default OrderType; 