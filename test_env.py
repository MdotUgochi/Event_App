import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("DATABASE_URL ->", DATABASE_URL)

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT version();"))
        print("✅ Connected successfully!")
        for row in result:
            print("Postgres version:", row[0])
except Exception as e:
    print("❌ Connection failed:", e)
