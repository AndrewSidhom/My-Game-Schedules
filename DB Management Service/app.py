import jwt
from flask import Flask, jsonify, make_response, request
from config import DevConfig

import sqlalchemy
from sqlalchemy import func
from sqlalchemy.orm import aliased
import datetime
import requests

app = Flask(__name__)
from models import db, row2dict, User, Team, Game, users_teams

app.config.from_object(DevConfig)

auth_service_url = 'http://localhost:5003'
my_secret = 'd1haeb1f1584fd5431c4250b2e859457'
auth_secret = "8fa70fd8b74bd9533537088f7e9d64ea"


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
    return jsonify({"code": 404, "msg": "404: Not Found"})


@app.route('/')
def microservice_root():
    return jsonify({'Microservice' : 'Database Management'})

@app.route("/user")
def get_all_user():
    user_list = User.query.all()
    return jsonify([row2dict(user) for user in user_list])


@app.route("/user/<user_id>")
def get_user(user_id):
    # id is a primary key, so we'll have max 1 result row
    user = User.query.filter_by(id=user_id).first()
    if user:
        return jsonify(row2dict(user))
    else:
        return jsonify({"code": 404, "msg": "Cannot find this user id."})


# request json parameters: "id" and "name"
@app.route("/user", methods={"POST"})
def add_user():
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    # get the name first, if no name then fail
    if not request.is_json:
        return jsonify({"code": 400, "msg": 'Bad request. Json expected'})
    json = request.get_json()
    name = json['name']
    if not name:
        return jsonify({"code": 403, "msg": "Cannot add user. Missing mandatory name field."})
    user_id = json['id']
    if not user_id:
        u = User(name=name)
    else:
        u = User(id=user_id, name=name)
    db.session.add(u)
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "Cannot add user."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 404, "msg": error})
    return jsonify({"code": 200, "msg": "success"})


@app.route("/team")
def get_all_team():
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    team_list = Team.query.all()
    return jsonify([row2dict(team) for team in team_list])


@app.route("/team/<team_id>")
def get_team(team_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    # id is a primary key, so we'll have max 1 result row
    team = Team.query.filter_by(id=team_id).first()
    if team:
        return jsonify(row2dict(team))
    else:
        return jsonify({"code": 404, "msg": "Cannot find this team id."})


@app.route("/user/<user_id>/team")
def get_fav_teams_of_user(user_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    user = User.query.filter_by(id=user_id).first()
    if user:
        team_list = user.fav_teams
        return jsonify([row2dict(team) for team in team_list])
    else:
        return jsonify({"code": 404, "msg": "Cannot find this user id."})


#request JSON parameters: "team_id"
@app.route("/user/<user_id>/team", methods={"POST"})
def add_team_to_fav_teams_of_user(user_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"code": 404, "msg": "Cannot find this user id."})
    if not request.is_json:
        return jsonify({"code": 400, "msg": 'Bad request. Json expected'})
    json = request.get_json()
    team_id = json['team_id']
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return jsonify({"code": 404, "msg": "Cannot find this team id."})
    user.fav_teams.append(team)
    db.session.add(user)
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "Cannot add team to user's favorite teams."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 404, "msg": error})
    return jsonify({"code": 200, "msg": "success"})


@app.route("/user/<user_id>/team/<team_id>", methods={"DELETE"})
def remove_team_from_fav_teams_of_user(user_id, team_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    user = User.query.filter_by(id=user_id).first()
    if not user:
        return jsonify({"code": 404, "msg": "Cannot find this user id."})
    team = Team.query.filter_by(id=team_id).first()
    if not team:
        return jsonify({"code": 404, "msg": "Cannot find this team id."})
    if team not in user.fav_teams:
        return jsonify({"code": 404, "msg": "This team id is not in this user's favorite teams list."})
    user.fav_teams.remove(team)
    db.session.add(user)
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "Cannot remove team from user's favorite teams."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 404, "msg": error})
    return jsonify({"code": 200, "msg": "success"})


@app.route("/team/<team_id>/game")
def get_all_games_of_team(team_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    team = Team.query.filter_by(id=team_id).first()
    if team:
        team_alias1 = aliased(Team)
        team_alias2 = aliased(Team)
        gamelist = db.session.query(Game.datetime,team_alias1.name,team_alias1.ranking,team_alias2.name,team_alias2.ranking).\
            join(team_alias1, Game.team1_id==team_alias1.id).\
            join(team_alias2, Game.team2_id==team_alias2.id).\
            filter((Game.team1_id == team_id) | (Game.team2_id == team_id)).all()
        gamesjson = [] # we will add to this empty json array each game's fields with the names of these fields
        for game in gamelist:
            jsonobj = {"Date & time": str(game[0])[:-3], "Team 1": game[1], "Team 1's ranking": game[2], "Team 2": game[3], "Team 2's ranking": game[4]}
            gamesjson.append(jsonobj)
        return jsonify(gamesjson)
    else:
        return jsonify({"code": 404, "msg": "Cannot find this team id."})


@app.route("/user/<user_id>/game")
def get_all_games_of_user(user_id):
    token = request.get_json()['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    user = User.query.filter_by(id=user_id).first()
    if user:
        subquery = db.session.query(users_teams.c.team_id).filter(users_teams.c.user_id==user_id).subquery()
        team_alias1 = aliased(Team)
        team_alias2 = aliased(Team)
        gamelist = db.session.query(Game.datetime, team_alias1.name, team_alias1.ranking, team_alias2.name, team_alias2.ranking).\
            join(team_alias1, Game.team1_id == team_alias1.id).\
            join(team_alias2, Game.team2_id == team_alias2.id).\
            filter(Game.team1_id.in_(subquery) | Game.team2_id.in_(subquery)).all()
        gamesjson = []  # we will add to this empty json array each game's fields with the names of these fields
        for game in gamelist:
            jsonobj = {"Date & time": str(game[0])[:-3], "Team 1": game[1], "Team 1's ranking": game[2],
                       "Team 2": game[3], "Team 2's ranking": game[4]}
            gamesjson.append(jsonobj)
        return jsonify(gamesjson)
    else:
        return jsonify({"code": 404, "msg": "Cannot find this user id."})


#updates the games in the db with the data supplied in json of the request
@app.route("/games", methods={"PUT"})
def update_games():
    if not request.is_json:
        return jsonify({"code": 400, "msg": "Bad request: Request data is not in JSON."})
    json = request.get_json()
    token = json['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)

    #First, clear old games...
    now = datetime.datetime.now()
    Game.query.filter(Game.datetime < now).delete()
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "A problem occured while clearing old games from the database."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 400, "msg": error})

    #Now add new games...
    jsongames = json['games']
    lastdatetime = db.session.query(Game.datetime, func.max(Game.datetime)).scalar()
    for jsongame in jsongames:
        datetimestr = str(jsongame['datetime'])
        datetimeobj = datetime.datetime.strptime(datetimestr, '%Y-%m-%d %H:%M:%S')
        if not lastdatetime or datetimeobj > lastdatetime:
            team1_id = jsongame['team1_id']
            team2_id = jsongame['team2_id']
            game = Game(datetime=datetimeobj, team1_id=team1_id, team2_id=team2_id)
            db.session.add(game)
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "One of the games could not be added to the database."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 400, "msg": error})
    return jsonify({"code": 200, "msg": "Games successfully updated"})


#updates the rankings of all 20 teams with the data supplied in json of the request
@app.route("/teams", methods={"PUT"})
def update_teams_rankings():
    if not request.is_json:
        return jsonify({"code": 400, "msg": "Bad request: Request data is not in JSON."})
    json = request.get_json()
    token = json['token']
    dict = decode_token(token)
    if dict['code'] != 200:
        return jsonify(dict)
    jsonrankings = json['rankings']
    for element in jsonrankings:
        db.session.query(Team).filter(Team.id == element['team_id']).update({"ranking": element['team_ranking']})
    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "One of the teams could not be updated with its new ranking info."
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return jsonify({"code": 400, "msg": error})
    return jsonify({"code": 200, "msg": "Teams successfully updated with their new rankings"})

if __name__ == '__main__':
    app.run()
