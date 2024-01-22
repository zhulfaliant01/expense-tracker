from datetime import datetime
from symbol import term
from flask import Flask, request
from db import connect_to_db

app = Flask(__name__)

connection = connect_to_db()

## Sql Script
CREATE_CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
category_id SERIAL PRIMARY KEY,
name VARCHAR NOT NULL,
budget NUMERIC,
budget_percentage NUMERIC )
"""

INSERT_CATEGORIES = """
INSERT INTO categories (name, budget, budget_percentage) VALUES (%s,%s,%s) RETURNING category_id;
"""

CREATE_CONTAINER_TABLE = """
CREATE TABLE IF NOT EXISTS container (
container_id SERIAL PRIMARY KEY,
name VARCHAR NOT NULL,
total_amount NUMERIC NOT NULL
)"""

INSERT_CONTAINER = """
INSERT INTO container (name, total_amount) VALUES (%s,%s) RETURNING container_id;
"""

GET_CATEGORIES_JSON = """
SELECT array_to_json(array_agg(row_to_json(categor)))
FROM (SELECT * FROM categories) categor 
"""

GET_CONTAINER_JSON = """
SELECT array_to_json(array_agg(row_to_json(containers)))
FROM (SELECT * FROM container) containers
"""

GET_CONTAINER_ID = """
SELECT array_to_json(array_agg(row_to_json(containers)))
FROM (SELECT * FROM container) containers
WHERE container_id = (%s)
"""

CREATE_TRANSACTION_TABLE = """
CREATE TABLE IF NOT EXISTS transaction (
transaction_id SERIAL PRIMARY KEY,
type VARCHAR CHECK (type IN ('Income', 'Expense', 'Transfer')),
amount NUMERIC NOT NULL,
category_id INT,
container_id INT,
transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
description TEXT,
FOREIGN KEY (category_id) REFERENCES categories(category_id),
FOREIGN KEY (container_id) REFERENCES container(container_id)
)"""

INSERT_TRANSACTION = """
INSERT INTO transaction (type, amount, category_id, container_id, transaction_date, description)
VALUES (%s, %s, %s, %s, %s, %s) RETURNING transaction_id
"""

GET_RECORD_BY_TERM_JSON = """
SELECT array_to_json(array_agg(row_to_json(transactions)))
FROM (SELECT *
FROM transaction
WHERE DATE(transaction_date) > (SELECT MAX(DATE(transaction_date)) - (%s) FROM transaction)) transactions
"""

GET_RECORD_BY_DATE_JSON = """
SELECT array_to_json(array_agg(row_to_json(transactions)))
FROM (SELECT *
FROM transaction
WHERE DATE(transaction_date) = DATE(%s)) transactions
"""

CONTAINER_TRIGGER = """
CREATE OR REPLACE FUNCTION update_cash_container()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE container
    SET total_amount = total_amount + NEW.amount
    WHERE container_id = NEW.container_id;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER after_transaction_insert
AFTER INSERT ON transaction
FOR EACH ROW
EXECUTE FUNCTION update_cash_container();
"""


@app.get("/")
def index():
    return "Welcome to the Sultan's Bank"


@app.route("/api/categories", methods=["GET", "POST"])
def categories():
    if request.method == "POST":
        data = request.get_json()

        name = data["name"]
        try:
            budget = data["budget"]
        except:
            budget = 0
        try:
            budget_percentage = data["budget_percentage"]
        except:
            budget_percentage = 0

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_CATEGORIES_TABLE)
                cursor.execute(INSERT_CATEGORIES, (name, budget, budget_percentage))
                category_id = cursor.fetchone()[0]
        return {
            "message": f"Category {name} added",
            "budget": budget,
            "category id": category_id,
        }, 201

    elif request.method == "GET":
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_CATEGORIES_JSON)
                json = cursor.fetchone()[0]
        return json


@app.route("/api/container", methods=["GET", "POST"])
def container():
    if request.method == "POST":
        data = request.get_json()

        name = data["name"]
        total_amount = int(data["total_amount"])

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_CONTAINER_TABLE)
                cursor.execute(INSERT_CONTAINER, (name, total_amount))
                container_id = cursor.fetchone()[0]
        return {
            "message": f"Container {name} added",
            "total_amount": total_amount,
            "container id": container_id,
        }, 201

    elif request.method == "GET":
        container_id = request.args.get("id")

        with connection:
            with connection.cursor() as cursor:
                if container_id is not None:
                    cursor.execute(GET_CONTAINER_ID, (container_id,))
                else:
                    cursor.execute(GET_CONTAINER_JSON)
                json = cursor.fetchone()[0]
        return json


@app.post("/api/transaction")
def input_transaction():
    data = request.get_json()

    type_ = data["type"]  # Income or Expense
    if type_ == "Expense":
        amount = -1 * int(data["amount"])
    elif type_ == "Income":
        amount = int(data["amount"])
    category_id = data["category_id"]
    container_id = data["container_id"]
    description = data["description"]

    try:
        date = datetime.strptime(data["date"], "%Y-%m-%d")
    except:
        date = datetime.now().strftime("%Y-%m-%d")

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_TRANSACTION_TABLE)
            cursor.execute(
                INSERT_TRANSACTION,
                (type_, amount, category_id, container_id, date, description),
            )
    return {"message": "Entry inserted."}, 201


@app.get("/api/transaction")
def get_record():
    term = request.args.get("term")
    date = request.args.get("date")

    if date is not None:
        # date should be in %Y-%m-%d
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_RECORD_BY_DATE_JSON, (date,))
                json = cursor.fetchone()[0]
        return json

    elif term is not None:
        terms = {"week": 7, "month": 30}
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_RECORD_BY_TERM_JSON, (terms[term],))
                json = cursor.fetchone()[0]
        return json


@app.post("/api/transfer")
def transfer():
    data = request.get_json()

    type_ = "Transfer"
    amount = int(data["amount"])
    from_container_id = data["from"]
    destination_container_id = data["destination"]
    try:
        date = data["date"]
    except:
        date = datetime.now().strftime("%Y-%m-%d")
    category_id = 1
    description = (
        f"Transfer from container {from_container_id} to {destination_container_id}"
    )

    with connection:
        with connection.cursor() as cursor:
            cursor.execute(
                INSERT_TRANSACTION,
                (
                    type_,
                    (-1 * amount),
                    category_id,
                    from_container_id,
                    date,
                    description,
                ),
            )  # Reduce the first container
            cursor.execute(
                INSERT_TRANSACTION,
                (
                    type_,
                    amount,
                    category_id,
                    destination_container_id,
                    date,
                    description,
                ),
            )  # Increase the second container
    return {"message": "Transfer added"}


## Add Trigger
with connection:
    with connection.cursor() as cursor:
        try:
            cursor.execute(CONTAINER_TRIGGER)
        except:
            pass

if __name__ == "__main__":
    app.run()
