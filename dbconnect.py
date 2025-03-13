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
    country = form_dict.get("country")
    state = form_dict.get("state")
    city = form_dict.get("city")
    age = form_dict.get("age")
    sex = form_dict.get("sex")
    email = form_dict.get("email")
    try :
        hash_password = generate_password_hash(password)
        cursor = connection.cursor()
        cursor.execute("INSERT INTO login (user_name, password) VALUES (%s, %s) RETURNING user_id;", (username, hash_password))
        login_id = cursor.fetchone()[0]
        cursor.execute(
                "INSERT INTO user_details (login_id, first_name, last_name, email, age, sex, country, city ,state) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                (login_id, first_name, last_name, email, age, sex, country, city, state)
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
        cursor.execute("SELECT first_name, last_name, email, age, sex, country, city, state FROM user_details WHERE login_id=%s", (user_id, ))
        records = cursor.fetchone()
        return records
    except Exception as e:
        print(f'Error : {e}')
    finally:
        cursor.close()

def insert_results(connection, user_id, form_data):
    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO risk_history 
            (user_id, mmse, functional, memory, behavior, adl, physical_activity, smoking, 
            alcohol, head_injury, hypertension, risk_score)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            user_id, form_data["mmse"], form_data["functional"], form_data["memory"],
            form_data["behavior"], form_data["adl"], form_data["physical_activity"], form_data["smoking"],
            form_data["alcohol"], form_data["head_injury"], form_data["hypertension"], form_data["risk_score"] * 100
        ) 
        cursor.execute(query, values)
        connection.commit() 
    except Exception as e:
        connection.rollback()
        print(f'Error: {e}')
    finally:
        cursor.close()

def to_track(connection, user_id):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT test_date, risk_score FROM risk_history WHERE user_id=%s ORDER BY test_date ASC", (user_id,))
        records = cursor.fetchall()
        return records
    except Exception as e:
        print(f'Error : {e}')
    finally:
        cursor.close()

def to_suggest(connection, user_id):
    try:
        cursor = connection.cursor()
        query = """
            SELECT physical_activity, smoking, alcohol, head_injury, hypertension 
            FROM risk_history 
            WHERE user_id = %s 
            ORDER BY test_date DESC  
            LIMIT 1
        """
        cursor.execute(query, (user_id,))
        result = cursor.fetchone()
        if result:
            factors = {
                "physical_activity": result[0],
                "smoking": result[1],
                "alcohol": result[2],
                "head_injury": result[3],
                "hypertension": result[4],
            }
            return factors
        else:
            return None  
    except Exception as e:
        print(f"Error fetching suggestions: {e}")
        return None
    finally:
        cursor.close()
