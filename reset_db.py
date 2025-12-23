from app import app, db
from models import Course, User, Registration, Slot

def reset_database():
    print("Resetting database...")
    with app.app_context():
        db.drop_all()
        print("Dropped all tables.")
        db.create_all()
        print("Created all tables with new schema.")
        print("Done.")

if __name__ == "__main__":
    reset_database()
