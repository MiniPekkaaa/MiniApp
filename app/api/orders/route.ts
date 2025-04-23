import { NextResponse } from 'next/server';
import clientPromise from '@/lib/mongodb';

export async function GET(request: Request) {
    try {
        const { searchParams } = new URL(request.url);
        const orgId = searchParams.get('orgId');

        if (!orgId) {
            return NextResponse.json({ error: 'orgId is required' }, { status: 400 });
        }

        const client = await clientPromise;
        const db = client.db("miniapp");
        
        // Получаем последние 5 заказов для организации, сортируя по дате
        const orders = await db.collection("orders")
            .find({ orgId: orgId })
            .sort({ date: -1 })
            .limit(5)
            .toArray();

        return NextResponse.json(orders);
    } catch (error) {
        console.error('Error fetching orders:', error);
        return NextResponse.json({ error: 'Failed to fetch orders' }, { status: 500 });
    }
} 