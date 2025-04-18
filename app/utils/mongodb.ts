import { MongoClient, ObjectId } from 'mongodb';

const uri = 'mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true';
const client = new MongoClient(uri);

export const createOrder = async (orderData: {
  _id: string;
  status: string;
  userid: string;
  username: string;
  process: string;
  positions: Array<{
    Beer_ID: number;
    Beer_Name: string;
    Legal_Entity: number;
    Beer_Count: number;
  }>;
}) => {
  try {
    await client.connect();
    const database = client.db('Pivo');
    const orders = database.collection('Orders');
    
    const result = await orders.insertOne({
      ...orderData,
      _id: new ObjectId(orderData._id),
      createdAt: new Date()
    });
    
    return result;
  } finally {
    await client.close();
  }
}; 