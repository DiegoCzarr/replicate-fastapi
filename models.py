from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    memberstack_id = Column(String, unique=True)
    email = Column(String)
    credits = Column(Integer, default=100)

class Creation(Base):
    __tablename__ = "creations"

    id = Column(Integer, primary_key=True)
    memberstack_id = Column(String)
    prompt = Column(Text)
    image_url = Column(Text)
    model = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
