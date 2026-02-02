import os
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class EmotionalState(Base):
    """Track Demi's emotional state with detailed persistence"""
    __tablename__ = 'emotional_states'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Core emotions
    loneliness = Column(Float, default=0.0)
    excitement = Column(Float, default=0.0)
    frustration = Column(Float, default=0.0)
    jealousy = Column(Float, default=0.0)
    vulnerable = Column(Boolean, default=False)

    # Emotional metadata
    interaction_context = Column(JSON, nullable=True)
    decay_multiplier = Column(Float, default=1.0)

    def __repr__(self):
        return f"<EmotionalState(timestamp={self.timestamp}, loneliness={self.loneliness})>"


class Interaction(Base):
    """Record individual interactions for emotional learning"""
    __tablename__ = 'interactions'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    platform = Column(String)  # e.g., 'discord', 'android'
    interaction_type = Column(String)  # e.g., 'message', 'ramble', 'command'
    content = Column(String)
    emotional_impact = Column(JSON)

    def __repr__(self):
        return f"<Interaction(platform={self.platform}, type={self.interaction_type})>"


class PlatformStatus(Base):
    """Track status of different platform integrations"""
    __tablename__ = 'platform_status'

    id = Column(Integer, primary_key=True)
    platform_name = Column(String, unique=True)
    enabled = Column(Boolean, default=False)
    last_active = Column(DateTime, nullable=True)
    connection_failures = Column(Integer, default=0)

    def __repr__(self):
        return f"<PlatformStatus(platform={self.platform_name}, enabled={self.enabled})>"
