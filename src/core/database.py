import os
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.core.config import DemiConfig
from src.core.logger import get_logger
from src.models.base import Base


class DatabaseManager:
    _instance = None

    def __new__(cls, config=None):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialize(config)
        return cls._instance

    def _initialize(self, config=None):
        """Initialize database connection"""
        if config is None:
            config = DemiConfig.load()

        logger = get_logger()

        # Ensure .demi directory exists
        demi_dir = Path(config.system.get("data_dir", "~/.demi")).expanduser()
        demi_dir.mkdir(parents=True, exist_ok=True)

        # Database path with robust handling
        db_path = demi_dir / "demi.sqlite"
        self.db_path = str(db_path)

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=config.system.get("debug", False),
        )

        # Create all tables
        Base.metadata.create_all(self.engine)

        # Configure session factory
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

        logger.info(f"Database initialized at {db_path}")

    @contextmanager
    def session_scope(self):
        """Provide a transactional scope around a series of operations."""
        session = self.Session()
        logger = get_logger()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database transaction failed: {e}")
            raise
        finally:
            session.close()

    def create_tables(self):
        """Force recreation of all tables"""
        logger = get_logger()
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.info("Database tables recreated")

    def get_session(self):
        """Get a new database session"""
        return self.Session()

    def close(self):
        """Close database connection"""
        logger = get_logger()
        self.Session.remove()
        self.engine.dispose()
        logger.info("Database connection closed")


# Global database manager instance
db_manager = DatabaseManager()
