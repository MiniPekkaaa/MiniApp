import React, { useState, useEffect } from 'react';
import { Button, Container, Typography, Box, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import { useNavigate } from 'react-router-dom';

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

const ManualOrder = () => {
  const [products, setProducts] = useState<BeerItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>('');
  const [quantity, setQuantity] = useState<number>(1);
  const navigate = useNavigate();
  const tg = window.Telegram.WebApp;

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await fetch('/api/products');
        const data = await response.json();
        setProducts(data);
      } catch (error) {
        console.error('Ошибка при загрузке продуктов:', error);
        tg.showAlert('Ошибка при загрузке списка продуктов');
      }
    };

    fetchProducts();
  }, []);

  const handleAddToCart = async () => {
    if (!selectedProduct) {
      tg.showAlert('Выберите товар');
      return;
    }

    const product = products.find(p => p.id.toString() === selectedProduct);
    if (!product) return;

    const cartItem = {
      ...product,
      quantity
    };

    try {
      const existingCart = JSON.parse(localStorage.getItem('cart') || '[]');
      const updatedCart = [...existingCart, cartItem];
      localStorage.setItem('cart', JSON.stringify(updatedCart));
      tg.showAlert('Товар добавлен в корзину');
      setSelectedProduct('');
      setQuantity(1);
    } catch (error) {
      console.error('Ошибка при добавлении в корзину:', error);
      tg.showAlert('Ошибка при добавлении в корзину');
    }
  };

  const handleMainMenu = () => {
    navigate('/');
  };

  return (
    <Container maxWidth="sm">
      <Box sx={{ mt: 4, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h5" component="h1" align="center">
          Добавление позиций
        </Typography>
        
        <FormControl fullWidth>
          <InputLabel>Выберите товар</InputLabel>
          <Select
            value={selectedProduct}
            onChange={(e) => setSelectedProduct(e.target.value)}
            label="Выберите товар"
          >
            {products.map((product) => (
              <MenuItem key={product.id} value={product.id.toString()}>
                {product.name} ({product.volume}л) - {product.price}₽
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <Button
            variant="outlined"
            onClick={() => setQuantity(Math.max(1, quantity - 1))}
          >
            -
          </Button>
          <Typography sx={{ mx: 2 }}>{quantity}</Typography>
          <Button
            variant="outlined"
            onClick={() => setQuantity(quantity + 1)}
          >
            +
          </Button>
        </Box>

        <Button
          variant="contained"
          fullWidth
          onClick={handleAddToCart}
        >
          Добавить в корзину
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

export default ManualOrder; 