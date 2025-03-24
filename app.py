import requests
import os
from flask import Flask, request, redirect, render_template, session, url_for
from datetime import timedelta, datetime
from dbconnect import *
import mmse_test as mt
import pickle
import pandas as pd
from sklearn.preprocessing import StandardScaler 
with open("alzheimer_prediction_model.pkl", "rb") as model_file:
    model = pickle.load(model_file)
with open("scaler.pkl", "rb") as scaler_file:
    scaler = pickle.load(scaler_file)
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "02ffcdcca96270df7c0cedfb28ac85f96e99aaec46b3d1fd2ce421e65c925604")
app.permanent_session_lifetime = timedelta(minutes=30)
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")

#index page routing
@app.route('/')
def show_index():
    return render_template('index.html')

#login page routing
@app.route('/login')
def show_login():
    return render_template('login.html')

@app.route('/login', methods=["POST"])
def login():
    username = request.form['username']
    password = request.form['password']
    connection = set_connection()
    if connection:
        user_id = login_user(connection, username, password)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            connection.close()
            return redirect('/')
        else :
            return render_template('login.html', error='\nLogin Failed! Are You Registered?\n')
    else :
        return render_template('login.html', error='Connection Error! Contact Support')
            
#signup page routing
@app.route('/signup')
def show_signup():
    return render_template('signup.html')

@app.route('/signup', methods=["POST"])
def signup():
    form_dict = request.form.to_dict()
    connection = set_connection()
    if connection :
        success = signup_user(connection, form_dict)
        connection.close()
        if success :
            return redirect('/login')
        else :
            return render_template('signup.html', error='\nSignup Failed! Contact Support\n')
    else:
        return render_template('signup.html', error='\nConnection Error')

#assess page routing
@app.route('/assess')
def show_assess():
    mmse_score = request.args.get('mmse_score', None)
    return render_template('assess.html', mmse_score=mmse_score)

@app.route('/submit-test', methods=["POST"])
def submit_test(): 
    try:
        form_data = {
            "mmse": float(request.form['mmse']),
            "memory": int(request.form['memory']),
            "behavior": int(request.form['behavior']),
            "physical_activity": int(request.form['physical_activity']),
            "smoking": int(request.form['smoking']),
            "alcohol": int(request.form['alcohol']),
            "head_injury": int(request.form['head_injury']),
            "hypertension": int(request.form['hypertension']),
        }

        form_data["functional_scores"] = [int(request.form.get(f'functional{i}', 0)) for i in range(1, 6)]
        form_data["functional"] = sum(form_data["functional_scores"])

        form_data["adl_scores"] = [int(request.form.get(f'adl{i}', 0)) for i in range(1, 6)]
        form_data["adl"] = sum(form_data["adl_scores"])

        print(form_data)

        input_data = pd.DataFrame([[form_data["mmse"], form_data["functional"], form_data["memory"], 
                                    form_data["behavior"], form_data["adl"]]],
                                  columns=['MMSE', 'FunctionalAssessment', 'MemoryComplaints', 'BehavioralProblems', 'ADL'])

        input_scaled = scaler.transform(input_data)

        prediction = model.predict(input_scaled)[0]
        probability = model.predict_proba(input_scaled)[0][1]
        form_data["risk_score"] = probability

        connection = set_connection()
        if connection and 'user_id' in session:
            insert_results(connection, session['user_id'], form_data)  
            connection.close()

        risk_percentage = f"{probability * 100:.2f}%"
        print(f"Risk Percentage: {risk_percentage}")

        return redirect('/profile')
    except Exception as e:
        print(f"Error : {e}")


#mmse test
@app.route('/mmse')
def show_mmse_test():
    return render_template('mmse_test.html')

@app.route('/calculate-mmse', methods=['POST'])
def calc_mmse():
    try:
        answers = request.form.to_dict()
        mmse_score = mt.is_date(answers['q1'])
        mmse_score += mt.is_month(answers['q2'])
        mmse_score += mt.is_year(answers['q3'])
        mmse_score += mt.is_weekday(answers['q4'])
        mmse_score += mt.is_noon(answers['q5'])
        connection = set_connection()
        if connection:
            user_details = return_user(connection, session['user_id'])
            connection.close()
        else:
            user_details =['none', 'none', 'none']
        mmse_score += 2 if (answers['q6'].lower())==user_details[-3].lower() else 0
        mmse_score += 1 if (answers['q7'].lower())==user_details[-1].lower() else 0     
        mmse_score += 2 if (answers['q8'].lower())==user_details[-2].lower() else 0
        mmse_score += mt.is_registering(answers['q9'])
        mmse_score += mt.is_attentive(answers['q10'])
        mmse_score += mt.is_registering(answers['q11'])
        mmse_score += mt.is_tools(answers['q12'])
        mmse_score += mt.is_sentence(answers['q13'])
        mmse_score += mt.is_tea_making(answers['q14'])
        mmse_score += mt.is_pentagon(answers['q15'])
        return redirect(url_for('show_assess', mmse_score=mmse_score))
    except Exception as e:
        print(f'Error : {e}')

#tracking route
@app.route('/track')
def show_track():
    connection = set_connection()
    if connection :
        results = to_track(connection, session['user_id'])
        if results:
            data_flag = True
            labels = [row[0].strftime('%Y-%m-%d') if row[0] else '' for row in results]  
            scores = [row[1] if row[1] is not None else 0 for row in results]
            current_score = scores[-1] if scores else None
            previous_score = scores[-2] if len(scores)>1 else None
            if previous_score is None or previous_score == 0:
                score_change = 100
            else :
                score_change = round(((current_score - previous_score) / previous_score) * 100, 1)
        else:
            labels, scores = [], [] 
            data_flag = False 
            score_change = None
            connection.close()
        return render_template('track.html', labels=labels, scores=scores, data_flag=data_flag, score_change=score_change)
    else :
        return render_template('track.html', error='\nConnection Error')

#profile routing
@app.route('/profile')
def show_profile():
    connection = set_connection()
    if connection:
        user_details = return_user(connection, session['user_id'])
        first_name, last_name, email, age, sex, country, city, state = user_details
        risk_details = to_track(connection, session['user_id'])
        score = risk_details[-1][1] if risk_details else False
        connection.close()
        return render_template('profile.html', first_name=first_name, last_name=last_name, email=email, age=age, sex=sex, score=score)
    return render_template('profile.html', error="Failed to fetch user details.")

#logout routing
@app.route('/logout')
def logout_user():
    session.clear()
    return redirect('/')

def get_mistral_suggestions(factors):
    """Generate AI-driven suggestions using Mistral API"""
    prompt = f"Based on these health factors {factors}, generate personalized advice to reduce Alzheimer's risk."

    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": "mistral-medium",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1024
    }

    try:
        print("Sending request to Mistral AI...")
        response = requests.post(url, headers=headers, json=data)

        print("Mistral AI Response Code:", response.status_code)
        print("Mistral AI Raw Response:", response.text)  # Debugging

        if response.status_code != 200:
            return f"API Error: {response.status_code} - {response.text}"

        result = response.json()
        print("Parsed Mistral Response:", result)  # Debugging

        # Extract response correctly
        return result.get("choices", [{}])[0].get("message", {}).get("content", "No insights available.")

    except Exception as e:
        print("Error calling Mistral API:", e)
        return "Error processing AI response."

@app.route('/suggest')
def suggest():
    try:
        print("MISTRAL_API_KEY:", MISTRAL_API_KEY)
        connection = set_connection()
        if not connection:
            return render_template('suggest.html', suggestions=[], error="Database connection failed")

        user_id = session.get('user_id')
        if not user_id:
            return redirect('/login')

        factors = to_suggest(connection, user_id)
        connection.close()

        if not factors:
            return render_template('suggest.html', suggestions=[], error="No data available to generate suggestions.")

        # Get AI-generated insights
        print("Sending request to Mistral AI...")

        ai_suggestions = get_mistral_suggestions(factors)

        return render_template('suggest.html', suggestions=[ai_suggestions])

    except Exception as e:
        print(f"Error generating suggestions: {e}")
        return render_template('suggest.html', suggestions=[], error="Internal Server Error")

#about page
@app.route('/about')
def show_about():
    return render_template("about.html")

#timeout protocol
@app.before_request
def check_session_timeout():
    session.permanent = True  
    if 'last_activity' in session:
        last_active = datetime.fromisoformat(session['last_activity']).replace(tzinfo=None) 
        if datetime.utcnow() - last_active > timedelta(minutes=30):
            session.clear()  
            return redirect('/')
    session['last_activity'] = datetime.utcnow().isoformat() 

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)