import jwt
from flask import Flask, jsonify, make_response, request
from datetime import date, timedelta
from dateutil.parser import parse
from dateutil import tz
import requests

app = Flask(__name__)

retrieval_token = '8b852ec3aebd42b3ae05bc1d75a38f9d'
db_service_url = 'http://localhost:5001'
auth_service_url = 'http://localhost:5003'

my_secret = 'a0adec1f1544fd3431c1120b2e859457'
auth_secret = "8fa70fd8b74bd9533537088f7e9d64ea"



def request_token():
    jsondata = {'request_type': 'ccg',
                'client_id': 'schedule_retriever',
                'client_secret': my_secret}
    r = requests.post(str(auth_service_url) + '/oauth/token', json=jsondata)
    try:
        return r.json()['access_token']
    except ValueError:
        return None


my_service_token = request_token()

def decode_token(auth_token):
    try:
        payload = jwt.decode(auth_token, auth_secret)
        return {"code": 200, "client": payload['client'], "msg": "success"}
    except jwt.ExpiredSignatureError:
        return {"code": 401, "msg": "Service Signature expired. Please log in again"}
    except jwt.InvalidTokenError:
        return {"code": 401, "msg": "Invalid service token. Please log in again"}


@app.errorhandler(404)
def page_not_found(e):
    return make_response(jsonify({"code": 404, "msg": "404: Not Found"}), 404)


@app.route('/')
def microservice_root():
    return jsonify({'Microservice' : 'Retrieval'})


#retrieve games from external API and send them to the DB service for the updates to be persisted there
@app.route('/games', methods={"PUT"})
def retrieve_games_update_db():
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code']!=200:
        return jsonify(dict)
    today = str(date.today())
    in13days = str(date.today()+timedelta(days=13))
    r = requests.get('http://api.football-data.org/v2/competitions/PL/matches?dateFrom='+today+'&dateTo='+in13days, headers={'X-Auth-Token': str(retrieval_token)})
    data = r.json()
    games = data['matches']  # games is a json array of json objects, retrieved from the external API
    games2 = []  # we will add to this empty json array only the relevant game info and in the end send it to the DB service
    for game in games:
        datetimeutc = parse(game['utcDate'])
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        datetimeutc = datetimeutc.replace(tzinfo=from_zone)
        datetimelocal = datetimeutc.astimezone(to_zone)
        datetimelocal = datetimelocal.replace(tzinfo=None) # after we've converted the retreived datetime to local datetime, we remove the timezone info
        jsonobj = {'datetime': str(datetimelocal), 'team1_id': game['homeTeam']['id'], 'team2_id': game['awayTeam']['id']}
        games2.append(jsonobj)

    r = requests.put(str(db_service_url)+'/games', json={'token': my_service_token, 'games': games2})
    try:
        return jsonify(r.json())
    except ValueError:
        return jsonify({'Error': r.text})


#retrieve updated team rankings from external API and send them to the DB service to be persisted there
@app.route('/teams', methods={"PUT"})
def retrieve_rankings_update_db():
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    r = requests.get('http://api.football-data.org/v2/competitions/PL/standings', headers={'X-Auth-Token': str(retrieval_token)})
    data = r.json()
    rankings = data['standings'][0]['table'] # rankings is a json array of json objects, retrieved from the external API
    rankings2 = [] # we will add to this empty json array only the relevant info and in the end send it to the DB service
    for element in rankings:
        team_id = element['team']['id']
        team_ranking = element['position']
        jsonobj = {'team_id': team_id, 'team_ranking': team_ranking}
        rankings2.append(jsonobj)
    r = requests.put(str(db_service_url)+'/teams', json={'token': my_service_token, 'rankings': rankings2})
    try:
        return jsonify(r.json())
    except ValueError:
        return jsonify({'Error': r.text})


if __name__ == '__main__':
    app.run()
