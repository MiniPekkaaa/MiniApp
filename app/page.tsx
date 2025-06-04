import { useEffect, useState } from 'react';
import { checkUserRegistration } from './utils/redis';
import Unauthorized from './components/Unauthorized';
import MainApp from './components/MainApp';

export default function Home() {
  const [isAuthorized, setIsAuthorized] = useState<boolean | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Здесь нужно получить userChatId из URL или другого источника
        const userChatId = '7944903241'; // Временно хардкодим для примера
        const isRegistered = await checkUserRegistration(userChatId);
        setIsAuthorized(isRegistered);
      } catch (error) {
        console.error('Error checking authorization:', error);
        setIsAuthorized(false);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, []);

  if (loading) {
    return <div>Загрузка...</div>;
  }

  return isAuthorized ? <MainApp /> : <Unauthorized />;
} 