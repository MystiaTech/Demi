import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.core.config import DemiConfig
from src.core.logger import logger
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

        # Ensure .demi directory exists
        demi_dir = os.path.expanduser('~/.demi')
        os.makedirs(demi_dir, exist_ok=True)

        # Database path with robust handling
        db_path = os.path.join(demi_dir, 'demi.sqlite')
        self.engine = create_engine(
            f'sqlite:///{db_path}',
            connect_args={'check_same_thread': False},
            echo=config.system.get('debug', False)
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
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(self.engine)
        logger.info("Database tables recreated")


# Global database manager instance
db_manager = DatabaseManager()
