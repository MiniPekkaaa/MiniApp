import { MongoClient, ObjectId } from 'mongodb';
import { MONGODB_URI } from '../../config';

const client = new MongoClient(MONGODB_URI);

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