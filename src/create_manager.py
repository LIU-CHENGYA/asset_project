import getpass
from .models.user import UserDB, UserRole
from .routers.auth import get_password_hash
from .database import engine
from sqlmodel import Session,select


def create_manager():
    with Session(engine) as session:
        existing_manager = session.exec(
            select(UserDB).where(
                UserDB.role == UserRole.ASSET_MANAGER
            )
        ).first()

        if existing_manager:
            print("Manager already exists.")
            return

        password = getpass.getpass("Enter manager password: ")

        manager = UserDB(
            name="System Manager",
            department="IT",
            role=UserRole.ASSET_MANAGER,
            hashed_password=get_password_hash(password),
        )

        session.add(manager)
        session.commit()

        print("Manager created successfully.")


if __name__ == "__main__":
    create_manager()