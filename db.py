import psycopg2

con = psycopg2.connect(
    database="expense_tracker",
    user="postgres",
    password="postgres",
    host="localhost",
    port="5432",
)
