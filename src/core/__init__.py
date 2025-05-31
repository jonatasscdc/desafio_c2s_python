# src/core/__init__.py
from .database import SessionLocal, engine, create_db_and_tables, AutomovelDB
__all__ = ["SessionLocal", "engine", "create_db_and_tables", "AutomovelDB"]