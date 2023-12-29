import psycopg2


def connect_to_db():
    try:
        return psycopg2.connect(
            database="expense_tracker",
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432",
        )
    except psycopg2.Error as e:
        print("Database connection error:", e)
        return None
