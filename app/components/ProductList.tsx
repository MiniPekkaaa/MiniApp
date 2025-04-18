import React from 'react';
import { Button } from '@mui/material';

interface Product {
  _id: string;
  id: number;
  name: string;
  fullName: string;
  volume: number;
  price: number;
  legalEntity: number;
}

const ProductList = ({ products }: { products: Product[] }) => {
  const addToCart = (product: Product) => {
    const cart = JSON.parse(localStorage.getItem('cart') || '[]');
    
    // Ищем товар в корзине
    const existingItemIndex = cart.findIndex((item: any) => item.id === product.id);
    
    if (existingItemIndex !== -1) {
      // Если товар уже есть, увеличиваем количество
      cart[existingItemIndex].quantity += 1;
    } else {
      // Если товара нет, добавляем новый с количеством 1
      cart.push({
        ...product,
        quantity: 1
      });
    }
    
    localStorage.setItem('cart', JSON.stringify(cart));
    window.Telegram.WebApp.showAlert('Товар добавлен в корзину');
  };

  return (
    <div style={{ padding: '20px' }}>
      {products.map((product) => (
        <div 
          key={product._id} 
          style={{
            marginBottom: '15px',
            padding: '15px',
            backgroundColor: 'rgba(82, 136, 193, 0.1)',
            borderRadius: '8px'
          }}
        >
          <div style={{ marginBottom: '10px' }}>
            <div style={{ fontWeight: 'bold' }}>{product.name}</div>
            <div style={{ fontSize: '0.9em', color: '#666' }}>{product.fullName}</div>
            <div>Объем: {product.volume}л</div>
            <div>Цена: {product.price}₽</div>
          </div>
          <Button
            variant="contained"
            onClick={() => addToCart(product)}
            fullWidth
            sx={{
              backgroundColor: '#5288c1',
              '&:hover': {
                backgroundColor: '#4476ac'
              }
            }}
          >
            Добавить в корзину
          </Button>
        </div>
      ))}
    </div>
  );
};

export default ProductList; 