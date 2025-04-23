'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

interface Order {
  id: string;
  date: string;
  status: string;
  itemsCount: number;
  totalAmount: number;
}

export default function MyOrders() {
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        // Получаем orgId из localStorage
        const orgId = localStorage.getItem('orgId');
        if (!orgId) {
          setError('Организация не найдена');
          return;
        }

        const response = await fetch(`/api/my-orders?orgId=${orgId}`);
        if (!response.ok) {
          throw new Error('Ошибка при загрузке заказов');
        }
        const data = await response.json();
        setOrders(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Произошла ошибка');
      } finally {
        setLoading(false);
      }
    };

    fetchOrders();
  }, []);

  const handleRepeatOrder = (orderId: string) => {
    router.push('/order-type');
  };

  if (loading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative">
          <strong className="font-bold">Ошибка!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-gray-800">Мои заказы</h1>
      {orders.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600">У вас пока нет заказов</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-lg overflow-hidden">
          {orders.map((order) => (
            <div key={order.id} className="border-b border-gray-200 last:border-b-0">
              <div className="p-6 hover:bg-gray-50 transition-colors duration-200">
                <div className="flex justify-between items-center mb-4">
                  <div className="flex items-center space-x-4">
                    <span className="text-lg font-semibold text-gray-800">
                      Заказ #{order.id.slice(-6)}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      order.status === 'новый' ? 'bg-blue-100 text-blue-800' :
                      order.status === 'в работе' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-green-100 text-green-800'
                    }`}>
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
                    <span>{order.date}</span>
                  </div>
                  <div>
                    <span className="block text-gray-500">Количество позиций</span>
                    <span>{order.itemsCount}</span>
                  </div>
                  <div>
                    <span className="block text-gray-500">Количество товаров</span>
                    <span>{order.totalAmount}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 