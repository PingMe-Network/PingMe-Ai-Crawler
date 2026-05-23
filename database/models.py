import os
from datetime import datetime
from dotenv import load_dotenv
from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()

# Lấy địa chỉ CSDL từ file .env, nếu không có thì báo lỗi
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("Chưa cấu hình DATABASE_URL trong file .env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class WebCrawl(Base):
    __tablename__ = "crawler_web_crawls"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(255), index=True)
    status = Column(String(50), default="pending")
    pages_crawled = Column(Integer, default=0)
    total_pages = Column(Integer, default=10)
    crawled_at = Column(DateTime, default=datetime.utcnow)

    rooms = relationship("ChatRoom", back_populates="web_crawl", cascade="all, delete-orphan")
    chunks = relationship("CrawlChunk", back_populates="web_crawl", cascade="all, delete-orphan")

class CrawlChunk(Base):
    __tablename__ = "crawler_chunks"

    id = Column(Integer, primary_key=True, index=True)
    web_crawl_id = Column(Integer, ForeignKey("crawler_web_crawls.id"))
    url = Column(String(500))
    content = Column(Text)
    embedding = Column(Vector(1536))

    web_crawl = relationship("WebCrawl", back_populates="chunks")

class ChatRoom(Base):
    __tablename__ = "crawler_chat_rooms"

    id = Column(Integer, primary_key=True, index=True)
    web_crawl_id = Column(Integer, ForeignKey("crawler_web_crawls.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    web_crawl = relationship("WebCrawl", back_populates="rooms")
    messages = relationship("ChatMessage", back_populates="room", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "crawler_chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("crawler_chat_rooms.id"))
    role = Column(String(50))
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("ChatRoom", back_populates="messages")

def init_db():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    Base.metadata.create_all(bind=engine)
