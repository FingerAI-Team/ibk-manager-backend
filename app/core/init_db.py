from app.core.database import Base, engine
from app.models.conversation import ConvLog, ClickedLog, StockCls

def init_db():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init_db()
    print("Database tables created successfully!") 