import { MongoClient } from 'mongodb';
import { NextResponse } from 'next/server';

const uri = 'mongodb://root:otlehjoq543680@46.101.121.75:27017/admin?authSource=admin&directConnection=true';

export async function GET(request: Request) {
    const client = new MongoClient(uri);
    
    try {
        const { searchParams } = new URL(request.url);
        const orgId = searchParams.get('orgId');

        if (!orgId) {
            return NextResponse.json({ error: 'orgId is required' }, { status: 400 });
        }

        await client.connect();
        const db = client.db('Pivo');
        
        // Получаем последние 5 заказов организации, сортируя по дате
        const orders = await db.collection('Orders')
            .find({ 
                org_ID: orgId 
            })
            .sort({ date: -1 })
            .limit(5)
            .toArray();

        // Форматируем заказы для отображения
        const formattedOrders = orders.map(order => ({
            id: order._id.toString(),
            date: order.date,
            status: order.status,
            itemsCount: Object.keys(order.Positions || {}).length,
            totalAmount: Object.values(order.Positions || {}).reduce((sum: number, pos: any) => 
                sum + (pos.Beer_Count || 0), 0)
        }));

        return NextResponse.json(formattedOrders);
    } catch (error) {
        console.error('Error fetching orders:', error);
        return NextResponse.json({ error: 'Failed to fetch orders' }, { status: 500 });
    } finally {
        await client.close();
    }
} 