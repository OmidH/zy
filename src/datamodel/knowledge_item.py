from sqlalchemy import Column, Integer, String
from .manager.sqldb_manager import Base, engine


class KnowledgeItem(Base):
    __tablename__ = 'knowledge_items'

    id = Column(Integer, primary_key=True)
    content = Column(String, nullable=False, index=True)


Base.metadata.create_all(bind=engine)
