from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ConvLog(Base):
    __tablename__ = 'ibk_convlog'
    __table_args__ = {'extend_existing': True}

    conv_id = Column(String(30), primary_key=True)
    date = Column(DateTime, nullable=False)
    qa = Column(String(10), nullable=False)
    content = Column(Text, nullable=False)
    user_id = Column(String(1024), nullable=False)
    
    # Relationships
    clicked = relationship("ClickedLog", back_populates="conv", cascade="all, delete")
    stock_cls = relationship("StockCls", back_populates="conv", cascade="all, delete")

class ClickedLog(Base):
    __tablename__ = 'ibk_clicked_tb'
    __table_args__ = {'extend_existing': True}

    conv_id = Column(String(30), ForeignKey('ibk_convlog.conv_id', ondelete='CASCADE'), primary_key=True)
    clicked = Column(String(10), nullable=False)
    user_id = Column(String(1024), nullable=False)
    
    # Relationship
    conv = relationship("ConvLog", back_populates="clicked")

class StockCls(Base):
    __tablename__ = 'ibk_stock_cls'
    __table_args__ = {'extend_existing': True}

    conv_id = Column(String(30), ForeignKey('ibk_convlog.conv_id', ondelete='CASCADE'), primary_key=True)
    ensemble = Column(String(10), nullable=False)
    gpt_res = Column(String(10), nullable=False)
    enc_res = Column(String(10), nullable=False)
    
    # Relationship
    conv = relationship("ConvLog", back_populates="stock_cls") 