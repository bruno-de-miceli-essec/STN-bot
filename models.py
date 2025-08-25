# models.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from db import Base
from datetime import datetime

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    login = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

class Form(Base):
    __tablename__ = "forms"
    id = Column(Integer, primary_key=True)
    google_form_id = Column(String, unique=True, nullable=False)   # ex: 1l1NZx...
    title = Column(String, nullable=True)
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", backref="forms")

class Response(Base):
    __tablename__ = "responses"
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False)
    email = Column(String, nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    response_uid = Column(String, nullable=True)  # si ta gateway renvoie un id unique
    __table_args__ = (UniqueConstraint("form_id", "email", "response_uid", name="uq_form_email_uid"),)

class FormCursor(Base):
    __tablename__ = "form_cursors"
    id = Column(Integer, primary_key=True)
    form_id = Column(Integer, ForeignKey("forms.id"), nullable=False, unique=True)
    last_seen_at = Column(DateTime, nullable=True)     # stratégie 1: par horodatage
    last_seen_uid = Column(String, nullable=True)      # stratégie 2: par ID unique