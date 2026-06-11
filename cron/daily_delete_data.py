"""
end_date가 오늘 이전인 공연을 event_db에서 삭제하는 스크립트.

환경변수:
  DATABASE_URL - PostgreSQL 접속 URL
"""
import os
import psycopg
from datetime import date

DB_URL = os.environ["DATABASE_URL"]


def _conn_str(url: str) -> str:
    return url.replace("postgresql+psycopg://", "postgresql://")


def main():
    today = date.today()
    print(f"[cleanup-expired] 시작: {today}")

    with psycopg.connect(_conn_str(DB_URL)) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM performances WHERE end_date < %s",
                (today,),
            )
            target_count = cur.fetchone()[0]
            print(f"삭제 대상: {target_count}건 (end_date < {today})")

            cur.execute(
                "DELETE FROM performances WHERE end_date < %s",
                (today,),
            )
            deleted = cur.rowcount
        conn.commit()

    print(f"삭제 완료: {deleted}건")


if __name__ == "__main__":
    main()
