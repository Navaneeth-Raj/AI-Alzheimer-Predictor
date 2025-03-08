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
app.secret_key = '02ffcdcca96270df7c0cedfb28ac85f96e99aaec46b3d1fd2ce421e65c925604'
app.permanent_session_lifetime = timedelta(minutes=30)

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
        mmse = float(request.form['mmse'])
        functional = float(request.form['functional'])
        memory = int(request.form['memory'])
        behavior = int(request.form['behavior'])
        adl = float(request.form['adl'])

        input_data = pd.DataFrame([[mmse, functional, memory, behavior, adl]],columns=['MMSE', 'FunctionalAssessment', 'MemoryComplaints', 'BehavioralProblems', 'ADL'])

        input_scaled = scaler.transform(input_data)

        prediction = model.predict(input_scaled)[0]
        probability = model.predict_proba(input_scaled)[0][1]

        connection = set_connection()
        if connection:
            insert_results(connection, session['user_id'], mmse, functional, memory, behavior, adl, probability)
        risk_percentage = f"{probability * 100:.2f}%"
        connection.close()
        return redirect('/profile')
    except Exception as e:
        import traceback
        print("Error during prediction:\n", traceback.format_exc())
        return f"Internal Server Error during prediction: {e}"

#mmse test
@app.route('/mmse')
def show_mmse_test():
    return render_template('mmse_test.html')

@app.route('/calculate-mmse', methods=['POST'])
def calc_mmse():
    try:
        answers = request.form.to_dict()
        mmse_score = mt.is_date(answers['q1'])
        print('q1',mmse_score)
        mmse_score += mt.is_month(answers['q2'])
        print('q2',mmse_score)
        mmse_score += mt.is_year(answers['q3'])
        print('q3',mmse_score)
        mmse_score += mt.is_weekday(answers['q4'])
        print('q4',mmse_score)
        mmse_score += mt.is_noon(answers['q5'])
        print('q5',mmse_score)
        """mmse_score += mt.is_state(answers['q6'])
        mmse_score += mt.is_country(answers['q7'])
        mmse_score += mt.is_city(answers['q8'])
        mmse_score += mt.is_building('q9')
        mmse_score += mt.is_room('q10')"""
        mmse_score += mt.is_registering(answers['q11'])
        print('q11',mmse_score)
        mmse_score += mt.is_attentive(answers['q12'])
        print('q12',mmse_score)
        mmse_score += mt.is_registering(answers['q13'])
        print('q13',mmse_score)
        mmse_score += mt.is_tools(answers['q14'])
        print('q14',mmse_score)
        mmse_score += mt.is_sentence(answers['q15'])
        print('q15',mmse_score)
        mmse_score += mt.is_tea_making(answers['q16'])
        print('q16',mmse_score)
        mmse_score += mt.is_pentagon(answers['q17'])
        print('q17',mmse_score)
        return redirect(url_for('show_assess', mmse_score=mmse_score))
    except Exception as e:
        print(f'Error : {e}')

#tracking route
@app.route('/track')
def show_track():
    connection = set_connection()
    if connection :
        results = get_result(connection, session['user_id'])
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
        first_name, last_name, email, age, sex = user_details
        risk_details = get_result(connection, session['user_id'])
        score = risk_details[-1][1] if risk_details else False
        connection.close()
        return render_template('profile.html', first_name=first_name, last_name=last_name, email=email, age=age, sex=sex, score=score)
    return render_template('profile.html', error="Failed to fetch user details.")

#logout routing
@app.route('/logout')
def logout_user():
    session.clear()
    return redirect('/')

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