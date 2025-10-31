from app.database import Base, SessionLocal, engine
from app.models import User
from app.security import get_password_hash


def seed_default_user() -> None:
    session = SessionLocal()
    try:
        email = "demo@wm.com"
        if session.query(User).filter(User.email == email).first():
            return
        user = User(
            company_id="WM-USA",
            company_name="Waste Management Demo",
            email=email,
            hashed_password=get_password_hash("changeme123"),
        )
        session.add(user)
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    seed_default_user()
    print("Seed completado. Usuario demo: demo@wm.com / changeme123")
