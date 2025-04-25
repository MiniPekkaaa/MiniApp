import { createClient } from 'redis';

const redisClient = createClient({
  password: 'otlehjoq',
  socket: {
    host: '46.101.121.75',
    port: 6379
  }
});

redisClient.on('error', err => console.error('Redis Client Error', err));

export const connectToRedis = async () => {
  if (!redisClient.isOpen) {
    await redisClient.connect();
  }
  return redisClient;
};

export const checkUserRegistration = async (userChatId: string) => {
  const client = await connectToRedis();
  const userData = await client.hGetAll(`beer:user:${userChatId}`);
  return (
    Object.keys(userData).length > 0 && 
    userData.UserChatID === userChatId &&
    userData.current_step === 'complete'
  );
};

export const getUserData = async (userChatId: string) => {
  const client = await connectToRedis();
  const userData = await client.hGetAll(`beer:user:${userChatId}`);
  return {
    organization: userData.organization || '',
    phone: userData.phone || '',
    name: userData.name || ''
  };
}; 