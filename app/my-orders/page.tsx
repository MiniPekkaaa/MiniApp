'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Order {
  id: number;
  date: string;
  itemsCount: number;
  totalAmount: number;
  status: 'новый' | 'в работе' | 'выполнен';
}

export default function MyOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const router = useRouter();

  // В реальном приложении здесь будет API-запрос
  useEffect(() => {
    // Моковые данные для демонстрации
    const mockOrders: Order[] = [
      {
        id: 1,
        date: '2024-03-20',
        itemsCount: 3,
        totalAmount: 1500,
        status: 'выполнен'
      },
      {
        id: 2,
        date: '2024-03-19',
        itemsCount: 2,
        totalAmount: 800,
        status: 'в работе'
      },
      {
        id: 3,
        date: '2024-03-18',
        itemsCount: 4,
        totalAmount: 2000,
        status: 'новый'
      },
      {
        id: 4,
        date: '2024-03-17',
        itemsCount: 1,
        totalAmount: 500,
        status: 'выполнен'
      },
      {
        id: 5,
        date: '2024-03-16',
        itemsCount: 2,
        totalAmount: 1200,
        status: 'выполнен'
      }
    ];
    setOrders(mockOrders);
  }, []);

  const handleRepeatOrder = (orderId: number) => {
    // Здесь будет логика повтора заказа
    console.log(`Повтор заказа ${orderId}`);
    router.push('/order-type');
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'новый':
        return 'bg-blue-100 text-blue-800';
      case 'в работе':
        return 'bg-yellow-100 text-yellow-800';
      case 'выполнен':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">Мои заказы</h1>
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {orders.map((order) => (
          <div key={order.id} className="border-b border-gray-200 last:border-b-0">
            <div className="p-6 hover:bg-gray-50 transition-colors duration-200">
              <div className="flex justify-between items-center mb-4">
                <div className="flex items-center space-x-4">
                  <span className="text-lg font-semibold text-gray-800">
                    Заказ #{order.id}
                  </span>
                  <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(order.status)}`}>
                    {order.status}
                  </span>
                </div>
                <button
                  onClick={() => handleRepeatOrder(order.id)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200 flex items-center space-x-2"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clipRule="evenodd" />
                  </svg>
                  <span>Повторить заказ</span>
                </button>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
                <div>
                  <span className="block text-gray-500">Дата заказа</span>
                  <span>{new Date(order.date).toLocaleDateString('ru-RU')}</span>
                </div>
                <div>
                  <span className="block text-gray-500">Количество позиций</span>
                  <span>{order.itemsCount}</span>
                </div>
                <div>
                  <span className="block text-gray-500">Сумма</span>
                  <span>{order.totalAmount} ₽</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
} 