'use client';

import { useRouter } from 'next/navigation';

export default function MainApp() {
  const router = useRouter();

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-8 text-center">Главное меню</h1>
      <div className="space-y-4">
        <button
          onClick={() => router.push('/order-type')}
          className="w-full p-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
        >
          Новый заказ
        </button>
        <button
          onClick={() => router.push('/my-orders')}
          className="w-full p-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors duration-200"
        >
          Мои заказы
        </button>
      </div>
    </div>
  );
} 