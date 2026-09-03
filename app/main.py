from .database import engine, Base
from .models import Payment


Base.metadata.create_all(bind=engine)

print("Database created successfully!")