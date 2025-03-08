import psycopg2 as db
from werkzeug.security import generate_password_hash, check_password_hash
import os #for Render

def set_connection():
    try :
        connection = db.connect(
            dbname = "Alzheimer's",
            user = "postgres",
            password = "accessdata",
            host = "localhost", 
            port = "5432"
        )
        return connection
    except db.Error as err:
        print(f"Error : {err}")
        return None 

def login_user(connection, username, password):
    try :
        cursor = connection.cursor()
        select_query = "SELECT user_id, password FROM login WHERE user_name = %s"
        cursor.execute(select_query, (username,))
        result = cursor.fetchone()
        if result is None:
            return False
        user_id, stored_password = result
        if check_password_hash(stored_password, password):
            return user_id
        return False
    except db.Error as err:
        print(f"Error : {err}")
        return "Query Failed"
    finally :
        cursor.close()
    
def signup_user(connection, form_dict):
    username = form_dict.get("username")
    password = form_dict.get("password")
    first_name = form_dict.get("first_name")
    last_name = form_dict.get("last_name")
    age = form_dict.get("age")
    sex = form_dict.get("sex")
    email = form_dict.get("email")
    try :
        hash_password = generate_password_hash(password)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO login (user_name, password) VALUES (%s, %s) RETURNING user_id;", (username, hash_password))
        login_id = cursor.fetchone()[0]
        cursor.execute(
                "INSERT INTO user_details (login_id, first_name, last_name, email, age, sex) VALUES (%s, %s, %s, %s, %s, %s);",
                (login_id, first_name, last_name, email, age, sex)
        )
        connection.commit()
        return True
    except Exception as e:
        connection.rollback()
        print(f'Error : {e}')
        return False
    finally :
        cursor.close()

def return_user(connection, user_id):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT first_name, last_name, email, age, sex FROM user_details WHERE login_id=%s", (user_id, ))
        records = cursor.fetchone()
        return records
    except Exception as e:
        print(f'Error : {e}')
    finally:
        cursor.close()

def insert_results(connection, user_id, mmse, functional, memory, behavior, adl, probability):
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO risk_history (user_id, mmse, functional, memory, behavior, adl, risk_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
        cursor.execute(query, (user_id, mmse, functional, memory, behavior, adl, probability * 100))
        connection.commit()
    except Exception as e:
        connection.rollback()
        print(f'Error : {e}')
    finally :
        cursor.close()

def get_result(connection, user_id):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT test_date, risk_score FROM risk_history WHERE user_id=%s ORDER BY test_date ASC", (user_id,))
        records = cursor.fetchall()
        return records
    except Exception as e:
        print(f'Error : {e}')
    finally:
        cursor.close()