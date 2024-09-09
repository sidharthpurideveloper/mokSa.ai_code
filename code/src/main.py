import random
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime, timedelta
import asyncio
import json
from aiocache import cached
# from kafka import KafkaConsumer  # Uncomment this when using a real Kafka setup

app = FastAPI()

DATABASE_URL = "sqlite:///./store_customers.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

class StoreCustomers(Base):
    __tablename__ = "store_customers"
    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(Integer, nullable=False)
    customers_in = Column(Integer, nullable=False)
    customers_out = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

async def process_message(message):
    db = SessionLocal()
    new_entry = StoreCustomers(
        store_id=message['store_id'],
        customers_in=message['customers_in'],
        customers_out=message['customers_out'],
        timestamp=datetime.now()
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    db.close()

# Mock Kafka message generator (commented out, for reference)
async def mock_kafka():
    while True:
        message = {
            'store_id': 10,
            'customers_in': random.randint(0, 5),
            'customers_out': random.randint(0, 5),
            'time_stamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        print(f"Generated mock message: {message}")
        await process_message(message)
        await asyncio.sleep(5)
        await broadcast_live_data(message)

# Real Kafka Consumer setup (commented out, for reference)
# async def kafka_consumer():
#     consumer = KafkaConsumer(
#         'your_topic_name',  # Replace with your Kafka topic name
#         bootstrap_servers='localhost:9092',  # Replace with your Kafka server details
#         auto_offset_reset='earliest',  # Consume from the earliest offset if you want all data
#         enable_auto_commit=True,
#         group_id='your_group_id',  # Replace with your group ID
#         value_deserializer=lambda x: json.loads(x.decode('utf-8'))
#     )
#     for message in consumer:
#         print(f"Consumed message: {message.value}")
#         await process_message(message.value)
#         await broadcast_live_data(message.value)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(mock_kafka())  # Start the mock Kafka generator
    # asyncio.create_task(kafka_consumer())  # Start consuming messages from Kafka

live_connections = []

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    history_data = await get_history_customers_data()
    await websocket.send_text(json.dumps({"history_data": history_data}))

    live_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        live_connections.remove(websocket)

async def broadcast_live_data(live_data):
    history_data = await get_history_customers_data()

    broadcast_data = {
        "live_data": live_data,
        "history_data": history_data
    }

    data = json.dumps(broadcast_data)
    for connection in live_connections:
        await connection.send_text(data)

@cached(ttl=5)
async def get_history_customers_data():
    db = SessionLocal()
    history_customers = db.query(
        StoreCustomers.store_id,
        func.sum(StoreCustomers.customers_in).label('total_in'),
        func.sum(StoreCustomers.customers_out).label('total_out'),
        func.strftime('%Y-%m-%d %H', StoreCustomers.timestamp).label('hour')
    ).filter(
        StoreCustomers.timestamp > datetime.utcnow() - timedelta(hours=24)
    ).group_by(
        StoreCustomers.store_id, 'hour'
    ).order_by(
        'hour'
    ).all()

    history_customers_list = [
        {
            "store_id": store_id,
            "total_in": total_in,
            "total_out": total_out,
            "hour": hour
        }
        for store_id, total_in, total_out, hour in history_customers
    ]
    
    db.close()
    return history_customers_list

@app.get("/api/history-customers")
async def get_history_customers():
    return await get_history_customers_data()
