# scanner.py
from __future__ import annotations
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db import Base

class Form(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    google_form_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=True)
    owner_user_id = Column(String, nullable=True)

    responses = relationship("Response", back_populates="form", cascade="all, delete-orphan")

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"), index=True, nullable=False)
    email = Column(String, index=True, nullable=False)
    submitted_at = Column(DateTime, nullable=True)

    form = relationship("Form", back_populates="responses")