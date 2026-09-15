"""期限を迎えた月を自動で締めるコマンド。"""
from app.db.session import SessionLocal
from app.services.monthly_close import close_due_month


def main() -> None:
    with SessionLocal() as session:
        year_month, closed = close_due_month(session)

    if closed:
        print(f"[monthly-close] {year_month} を締めました")
    else:
        print(f"[monthly-close] {year_month} は締め済みです")


if __name__ == "__main__":
    main()
