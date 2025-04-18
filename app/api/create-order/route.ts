import { MongoClient } from 'mongodb';
import { NextResponse } from 'next/server';

const uri = 'mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true';

export async function POST(request: Request) {
  try {
    const client = new MongoClient(uri);
    const { userId, items } = await request.json();

    await client.connect();
    const db = client.db('Pivo');
    
    const result = await db.collection('Orders').insertOne({
      _id: new Date().getTime().toString(),
      status: "in work",
      userid: userId.toString(),
      username: "ООО Пивной мир",
      process: "промежуточный процесс добавления пива",
      positions: items.map((item: any) => ({
        Beer_ID: parseInt(item.id),
        Beer_Name: item.name,
        Legal_Entity: item.legalEntity || 2,
        Beer_Count: parseInt(item.quantity)
      }))
    });

    await client.close();

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error creating order:', error);
    return NextResponse.json({ success: false, error: 'Failed to create order' }, { status: 500 });
  }
} 