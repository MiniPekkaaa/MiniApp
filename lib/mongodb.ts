import { MongoClient } from 'mongodb';

if (!process.env.MONGODB_URI) {
    throw new Error('Invalid/Missing environment variable: "MONGODB_URI"');
}

const uri = process.env.MONGODB_URI;
const options = {};

let client;
let clientPromise: Promise<MongoClient>;

if (process.env.NODE_ENV === 'development') {
    // В режиме разработки используем глобальную переменную для сохранения соединения
    let globalWithMongo = global as typeof globalThis & {
        _mongoClientPromise?: Promise<MongoClient>
    };

    if (!globalWithMongo._mongoClientPromise) {
        client = new MongoClient(uri, options);
        globalWithMongo._mongoClientPromise = client.connect();
    }
    clientPromise = globalWithMongo._mongoClientPromise;
} else {
    // В продакшене создаем новое соединение
    client = new MongoClient(uri, options);
    clientPromise = client.connect();
}

export default clientPromise; 