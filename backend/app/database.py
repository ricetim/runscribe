from sqlmodel import SQLModel, create_engine, Session, select
from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def _add_column(conn, table: str, column: str, col_type: str) -> None:
    """Add a column to a table if it does not already exist."""
    try:
        conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except Exception:
        pass  # column already exists


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)
    # Incremental column migrations for existing databases
    with engine.connect() as conn:
        _add_column(conn, "datapoint", "vertical_oscillation_mm", "REAL")
        _add_column(conn, "datapoint", "stride_length_m", "REAL")
        _add_column(conn, "datapoint", "vertical_ratio", "REAL")
        _add_column(conn, "datapoint", "stance_time_ms", "REAL")
        _add_column(conn, "activity", "rpe", "INTEGER")
        _add_column(conn, "activity", "name", "TEXT")
        _add_column(conn, "plannedworkout", "optional", "INTEGER DEFAULT 0")
        conn.commit()
    # Seed singleton UserProfile if not present
    from app.models import UserProfile
    with Session(engine) as session:
        if not session.get(UserProfile, 1):
            session.add(UserProfile(id=1))
            session.commit()


def get_session():
    with Session(engine) as session:
        yield session
