import os
import psycopg2
import datetime
from dotenv import load_dotenv
from flask import Flask, request
from db import con

app = Flask(__name__)

# load_dotenv()  # loads variables from .env file into environment

connection = con


@app.get("/")
def index():
    return "Welcome to the Sultan's Bank"


@app.route("/api/categories", methods=["GET", "POST", "DELETE"])
def categories():
    if request.method == "POST":
        CREATE_CATEGORIES_TABLE = """CREATE TABLE IF NOT EXISTS categories (
        category_id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        budget NUMERIC,
        budget_percentage NUMERIC
        )"""

        INSERT_CONTAINER = """
        INSERT INTO categories (name, budget, budget_percentage) VALUES (%s,%s,%s) RETURNING category_id;
        """

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
                cursor.execute(INSERT_CONTAINER, (name, budget, budget_percentage))

        return {
            "message": f"Categorie {name} added",
            "budget": f"Budget : {budget}",
        }, 201

    elif request.method == "GET":
        GET_CATEGORIES_JSON = """
        SELECT array_to_json(array_agg(row_to_json(categor)))
        FROM (SELECT * FROM categories) categor 
        """

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_CATEGORIES_JSON)
                json = cursor.fetchone()[0]
        return json


@app.route("/api/container", methods=["GET", "POST", "DELETE"])
def container():
    if request.method == "POST":
        CREATE_CONTAINER_TABLE = """
        CREATE TABLE IF NOT EXISTS container (
        container_id SERIAL PRIMARY KEY,
        name VARCHAR NOT NULL,
        total_amount NUMERIC NOT NULL
        )"""

        INSERT_CONTAINER = """
        INSERT INTO container (name, total_amount) VALUES (%s,%s) RETURNING container_id;
        """

        data = request.get_json()

        name = data["name"]
        total_amount = int(data["total_amount"])

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_CONTAINER_TABLE)
                cursor.execute(INSERT_CONTAINER, (name, total_amount))

        return {
            "message": f"Container {name} added",
            "total_amount": f"Total amount : {total_amount}",
        }, 201

    elif request.method == "GET":
        GET_CONTAINER_JSON = """
        SELECT array_to_json(array_agg(row_to_json(containers)))
        FROM (SELECT * FROM container) containers
        """

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(GET_CONTAINER_JSON)
                json = cursor.fetchone()[0]
        return json


@app.route("/api/transaction", methods=["GET", "POST", "DELETE"])
def input_transaction():
    if request.method == "POST":
        CREATE_TRANSACTION_TABLE = """CREATE TABLE IF NOT EXISTS transaction (
        transaction_id SERIAL PRIMARY KEY,
        type VARCHAR CHECK (type IN ('Income', 'Expense')),
        amount NUMERIC NOT NULL,
        category_id INT,
        container_id INT,
        transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        description TEXT,
        FOREIGN KEY (category_id) REFERENCES Categories(category_id),
        FOREIGN KEY (container_id) REFERENCES CashContainer(container_id)
        )"""

        INSERT_TRANSACTION = """
        INSERT INTO transaction (type, amount, category_id, container_id, transaction_date, description)
        VALUES (%s, %s, %s, %s, %s, %s) RETURNING transaction_id
        """

        data = request.get_json()

        type_ = data["type"]
        amount = data["amount"]
        category_id = data["category_id"]
        container_id = data["container_id"]
        description = data["description"]

        try:
            date = datetime.strptime(data["date"], "%d-%m-%Y")
        except:
            date = datetime.now()

        with connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_TRANSACTION_TABLE)
                cursor.execute(
                    INSERT_ENTRY,
                    (type_, amount, category_id, container_id, date, description),
                )
        return {"message": "Entry inserted."}, 201

    elif request.method == "GET":
        GET_TRANSACTION


# @app.get("/api/container/current")
# def get_current():
#     data = request.get_json()


# @app.get("/api/transaction/history-week")
# def get_week():
#     data = request.get_json()


# @app.get("/api/trasaction/history-month")
# def get_month():
#     data = request.get_json()

# @app.get("/api/trasaction/<start>,<end>")
# def get_month():
#     data = request.get_json()


if __name__ == "__main__":
    app.run()
