# import the Flask class from the flask module
import jwt
import requests
from flask import Flask, jsonify, render_template, redirect, url_for, request, session

# create the application object
app = Flask(__name__)

# config
my_secret = 'f0fdeb1f1584fd5431c4250b2e859457'
app.secret_key = my_secret
auth_secret = "8fa70fd8b74bd9533537088f7e9d64ea"

last_login = None

FE_SERVICE_URL = 'http://localhost:5000'
DB_SERVICE_URL = 'http://localhost:5001'
RETRIEVAL_SERVICE_URL = 'http://localhost:5002'
AUTH_SERVICE_URL = 'http://localhost:5003'


def request_service_token():
    json = {'request_type': 'ccg',
            'client_id': 'front_end',
            'client_secret': my_secret}
    response = requests.post(AUTH_SERVICE_URL + '/oauth/token', json=json)
    try:
        return response.json()['access_token']
    except ValueError:
        return None


my_service_token = request_service_token()


def decode_token(auth_token):
    try:
        payload = jwt.decode(auth_token, auth_secret)
        return {"code": 200, "user": payload['user'], "msg": "success"}
    except jwt.ExpiredSignatureError:
        return {"code": 401, "msg": "User Signature expired. Please log in again"}
    except jwt.InvalidTokenError:
        return {"code": 401, "msg": "Invalid user token. Please log in again"}


# use decorators to link the function to a url
@app.route('/')
def home():
    return jsonify({"Microservice": "Front End"})


@app.route('/welcome', methods=['GET', 'POST'])
def welcome():
    # Verify user token
    if not session['user_token_p1'] or not session['user_token_p2'] or not session['user_token_p3'] or not session['user_id']:
        return jsonify({"code": 500, "msg": "Could not retrieve session variables"})
    user_token = session.get('user_token_p1') + '.' + session.get('user_token_p2') + '.' + session.get('user_token_p3')
    dict = decode_token(user_token)
    if dict['code'] != 200:
        return jsonify(dict)

    if not my_service_token:
        return jsonify(
            {"code": 500, "msg": "Front End could not get the token to access other backend services"})

    if request.method == 'POST': # this is a request to "refresh" homepage, which means updating our database first
        response = requests.put(str(RETRIEVAL_SERVICE_URL) + '/games', json={'token': my_service_token})
        try:
            response = response.json()
        except ValueError:
            return jsonify({'Error': response.text})
        if response['code'] != 200:
            return jsonify(response.json())
        response = requests.put(str(RETRIEVAL_SERVICE_URL) + '/teams', json={'token': my_service_token})
        try:
            response = response.json()
        except ValueError:
            return jsonify({'Error': response.text})
        if response['code'] != 200:
            return jsonify(response.json())

    # Whether GET or POST, now get schedules to display
    user_id = session.get("user_id")
    response = requests.get(str(DB_SERVICE_URL) + "/user/" + str(user_id) + "/game", json={"token": my_service_token})
    req_data = None
    try:
        req_data = response.json()
    except ValueError:
        return jsonify({'Error': response.text})
    return render_template('welcome.html', req_data=req_data)




# route for handling the login page logic
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        if not my_service_token:
            return jsonify(
                {"code": 500, "msg": "Front End could not get the token to access other backend services"})

        username = request.form['username']
        password = request.form['password']
        response = requests.post(str(AUTH_SERVICE_URL) + '/login', auth=(username, password), json={'token': my_service_token})
        try:
            response = response.json()
        except ValueError:
            return jsonify({'Error': response.text})

        if response['code'] == 200: #user has been authenticated with auth service
            user_token = response['token']
            user_token_parts = user_token.split('.')
            session['user_token_p1'] = user_token_parts[0]
            session['user_token_p2'] = user_token_parts[1]
            session['user_token_p3'] = user_token_parts[2]
            user_id = response['id']
            session['user_id'] = user_id

            # if this is the first login or if last login was more than an hour ago, call retrieval service to get data & update db
            # if not last_login or (datetime.datetime.now() > last_login + datetime.timedelta(hours=1)):
            #     response = requests.put(str(RETRIEVAL_SERVICE_URL) + '/games', json={'token': my_service_token})
            #     try:
            #         response = response.json()
            #     except ValueError:
            #         return jsonify({'Error': response.text})
            #     if response['code'] != 200:
            #         return jsonify(response.json())
            #     response = requests.put(str(RETRIEVAL_SERVICE_URL) + '/teams', json={'token': my_service_token})
            #     try:
            #         response = response.json()
            #     except ValueError:
            #         return jsonify({'Error': response.text})
            #     if response['code'] != 200:
            #         return jsonify(response.json())
            #     last_login = datetime.datetime.now()

            response = requests.get(str(DB_SERVICE_URL) + "/user/" + str(user_id) + "/game", json={"token": my_service_token})
            req_data = None
            try:
                req_data = response.json()
            except ValueError:
                return jsonify({'Error': response.text})
            return render_template('welcome.html', req_data=req_data)  # Home page will need to display json
        else: # response code is not 200, user has not been authenticated with auth service
            return jsonify(response)
    else: # request method is GET
        return render_template('login.html')


# route for handling the logout page logic
@app.route('/logout')
# @login_required
def logout():
    session.pop('logged_in', None)
    session.pop('user_id', None)
    session.pop('user_token_p1', None)
    session.pop('user_token_p2', None)
    session.pop('user_token_p3', None)
    return redirect(url_for('login'))


# route for handling the register page logic
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if not my_service_token:
            return jsonify(
                {"code": 500, "msg": "Front End could not get the token to access other backend services"})
        username = request.form['username']
        password = request.form['password']
        response = requests.post(AUTH_SERVICE_URL + "/register", json={"name": username, "password": password, "token":my_service_token})
        try:
            response = response.json()
        except ValueError:
            return jsonify({'Error': response.text})
        if response['code'] == 200:
            return jsonify(response)
        else:
            return jsonify(response)
    else: # request method is GET
        return render_template('register.html')


# # route for handling team info logic
# @app.route('/teams', methods=['GET', 'POST'])
# def teams():
#     return render_template('teams.html', user=user_details)


# # route for handling team schedules logic
# @app.route('/teams/<int:team_id>/schedules')
# def schedules(team_id):
#     return render_template('teams.html', user=user_details)


# route for adding a team to user's favorites
@app.route('/myteams', methods=['GET', 'POST'])
def myteams():
    #Verify user token
    if not session['user_token_p1'] or not session['user_token_p2'] or not session['user_token_p3'] or not session['user_id']:
        return jsonify({"code": 500, "msg": "Could not retrieve session variables"})
    user_token = session.get('user_token_p1') + '.' + session.get('user_token_p2') + '.' + session.get('user_token_p3')
    dict = decode_token(user_token)
    if dict['code'] != 200:
        return jsonify(dict)

    if request.method == 'POST':
        if not my_service_token:
            return jsonify(
                {"code": 500, "msg": "Front End could not get the token to access other backend services"})
        selected = request.form['mySelect']
        switcher = {
            'Liverpool': 64,
            'Man City': 65,
            'Tottenham': 73,
            'Arsenal': 57,
            'Man United': 66,
            'Chelsea': 61,
            'Wolverhampton': 76,
            'Watford': 346,
            'West Ham': 563,
            'Leicester City': 338,
            'Everton': 62,
            'Bournemouth': 1044,
            'Newcastle': 67,
            'Crystal Palace': 354,
            'Brighton Hove': 397,
            'Southampton': 340,
            'Burnley': 328,
            'Cardiff': 715,
            'Fulham': 63,
            'Huddersfield': 394
        }
        team_id = switcher.get(selected, "Invalid team name")
        user_id = session.get("user_id")
        response = requests.post(DB_SERVICE_URL + "/user/" + str(user_id) +"/team",
                                 json={"team_id": team_id, "token": my_service_token})
        try:
            response = response.json()
            return jsonify(response)
        except ValueError:
            return jsonify({'Error': response.text})
    else:
        return render_template('addTeam.html')


# route for initiating the "delete team" use case. It takes the user's choice of a team to delete and issues a request to the following endpoint: DELETE /myteams/<int:team_id>
@app.route('/deleteteam', methods=['GET', 'POST'])
def deleteteam():
    if request.method == 'GET':
        return render_template('deleteTeam.html')
    else:
        selected = request.form['mySelect']
        switcher = {
            'Liverpool': 64,
            'Man City': 65,
            'Tottenham': 73,
            'Arsenal': 57,
            'Man United': 66,
            'Chelsea': 61,
            'Wolverhampton': 76,
            'Watford': 346,
            'West Ham': 563,
            'Leicester City': 338,
            'Everton': 62,
            'Bournemouth': 1044,
            'Newcastle': 67,
            'Crystal Palace': 354,
            'Brighton Hove': 397,
            'Southampton': 340,
            'Burnley': 328,
            'Cardiff': 715,
            'Fulham': 63,
            'Huddersfield': 394
        }
        if not session['user_id']:
            return jsonify({"code": 500, "msg": "Could not retrieve session variables"})
        user_id = session['user_id']
        team_id = switcher.get(selected, "Invalid team name")
        response = requests.delete(FE_SERVICE_URL + "/myteams/" + str(team_id), json={"user_id": user_id})
        try:
            response = response.json()
            return jsonify(response)
        except ValueError:
            return jsonify({'Error': response.text})


# route for deleting a team from user's favorites
@app.route('/myteams/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    if not my_service_token:
        return jsonify(
            {"code": 500, "msg": "Front End could not get the token to access other backend services"})

    if not request.is_json:
        return jsonify({"code": 400, "msg": "Bad request. Json expected"})
    json = request.get_json()
    user_id = json['user_id']
    response = requests.delete(DB_SERVICE_URL + "/user/" + str(user_id) + "/team/" + str(team_id),
                             json={"token": my_service_token})
    try:
        response = response.json()
        return jsonify(response)
    except ValueError:
        return jsonify({'Error': response.text})


#start the server with the 'run()' method
if __name__ == '__main__':
    app.run(debug=True)

