import React from 'react';
import { Button, Typography, Box } from '@mui/material';

const Unauthorized = () => {
  const handleRedirectToBot = () => {
    window.open('https://t.me/your_bot_name', '_blank');
  };

  return (
    <Box
      display="flex"
      flexDirection="column"
      alignItems="center"
      justifyContent="center"
      minHeight="100vh"
      gap={3}
    >
      <Typography variant="h5" component="h1" textAlign="center">
        Вы не зарегистрированы в системе
      </Typography>
      <Button 
        variant="contained" 
        color="primary"
        onClick={handleRedirectToBot}
      >
        Пройти регистрацию в боте
      </Button>
    </Box>
  );
};

export default Unauthorized; 