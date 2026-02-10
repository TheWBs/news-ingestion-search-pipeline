import os
import pymysql

def main():
    host = os.environ["DB_HOST"]
    port = int(os.environ.get("DB_PORT", "3306"))
    user = os.environ["DB_USER"]
    password = os.environ["DB_PASSWORD"]
    db = os.environ["DB_NAME"]

    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        charset="utf8mb4",
        autocommit=True,
    )

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM urls;")
        (cnt,) = cur.fetchone()
        print(f"✅ Connected to MariaDB. urls count = {cnt}")

    conn.close()

if __name__ == "__main__":
    main()
