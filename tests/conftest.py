import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from orca.model import (  # noqa: F401
    Base,
    CommonMixin,
    Document,
    Image,
    Megadoc,
    Search,
    StatusMixin,
)


# Fixture to create an in-memory SQLite database
@pytest.fixture(scope="function")
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(engine)
