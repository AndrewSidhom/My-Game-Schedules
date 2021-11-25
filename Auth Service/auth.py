from flask import Blueprint, jsonify, make_response, request
from app import app
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User
from requests import Session
from functools import wraps

import sqlalchemy
import requests
import time
import jwt
import hmac
import json

auth = Blueprint("auth", __name__)
db.create_all()

_auth_server = "http://localhost:5000"
_data_server = "http://localhost:5001"
_TOKEN = None
_auth_data = [("client_id", "auth_service"),
              ("client_secret", "85fdeb1f1584fdac31c4250b2e859123"),
              ("request_type", "acg")]


server = 'http://localhost:5000'
secret = '85fdeb1f1584fdac31c4250b2e859123'

SECRET = "8fa70fd8b74bd9533537088f7e9d64ea"
_Client_SECRETS = {'front_end': 'f0fdeb1f1584fd5431c4250b2e859457', 'schedule_retriever': 'a0adec1f1544fd3431c1120b2e859457', 'db_management': 'd1haeb1f1584fd5431c4250b2e859457'}


def setup_connector(app_name, name='default', **options):
    global _TOKEN
    if not hasattr(app_name, 'extensions'):
        app_name.extensions = {}
    if 'connectors' not in app_name.extensions:
        app_name.extensions['connectors'] = {}
    session = Session()
    if 'auth' in options:
        session.auth = options['auth']
    headers = options.get('headers', {})
    if 'Content-Type' not in headers:
        headers['Content-Type'] = 'application/json'
    _TOKEN = get_token()
    headers['Authorization'] = _TOKEN.decode('UTF-8')
    session.headers.update(headers)
    app_name.extensions['connectors'][name] = session
    return session


def get_token():
    now = int(time.time())
    token = {'iss': 'https://tokendealer.gameschedules.io',
             'iat': now,
             'exp': now + 3600 * 24,
             "client": "auth_service.game_schedules.io"}
    token = jwt.encode(token, SECRET, algorithm="HS256")
    return token


def get_connector(app_name, name='default'):
    setup_connector(app)
    connector = app_name.extensions['connectors'][name]
    return connector


def create_service_token(data):
    now = int(time.time())
    token = {'iss': 'https://tokendealer.gameschedules.io',
             'iat': now,
             'exp': now + 3600 * 24,
             "client": data['client_id'] + "_game_schedules.io"}
    token = jwt.encode(token, SECRET, algorithm="HS256")
    return token


def create_user_token(u_name):
    now = int(time.time())
    token = {'user': u_name,
             'iss': 'https://tokendealer.example.com',
             'iat': now,
             'exp': now + 1800
             }
    token = jwt.encode(token, SECRET, algorithm="HS256")
    return token


def is_authorized_app(client_id, client_secret):
    actual_secret = _Client_SECRETS.get(client_id)
    return hmac.compare_digest(actual_secret, client_secret)


def call_data_service(user_data):
    response = requests.post("http://localhost:5001/user", json=user_data)
    return response.json()


@auth.route("/register", methods=["POST"])
def create_users():
    data = request.get_json()
    name = data['name']
    password = data['password']
    if not name and not password:
        return make_response(jsonify({"code": 400,
                                      "msg": "Missing Required Information"}), 400)
    u = User.query.filter_by(name=name).first()
    if u:
        return make_response(jsonify({"code": 409,
                                      "msg": "user account already exists"}), 409)
    hashed_password = generate_password_hash(password, method='sha256')
    print(hashed_password)

    u = User(password=hashed_password, name=name, admin=False)
    db.session.add(u)

    try:
        db.session.commit()
    except sqlalchemy.exc.SQLAlchemyError as e:
        error = "Cannot put this user. "
        print(app.config.get("DEBUG"))
        if app.config.get("DEBUG"):
            error += str(e)
        return make_response(jsonify({"code": 404, "msg": error}), 404)
    token = get_token()
    user_data = {"id": u.id, "name": u.name, "token": token.decode('UTF-8')}
    responsejson = call_data_service(user_data)
    if responsejson['code']==200:
        return jsonify({"code": 200, "msg": "success"})
    else:
        return jsonify({"code": 500, "msg": "User could not be added to DB"})


@auth.route("/login", methods=["POST"])
def authenticate():
    a = request
    login = request.authorization

    if not login or not login.username or not login.password:
        return make_response(jsonify({"code": 400,
                                      "msg": "bad request"}), 400)

    user = User.query.filter_by(name=login.username).first()
    if not user:
        return make_response(jsonify({"code": 403,
                                      "msg": "access forbidden"}), 403)
    if check_password_hash(user.password, login.password):
        # generate token for the user
        user_token = create_user_token(login.username)
        return jsonify({"code": 200, "msg": "success", "token": user_token.decode('UTF-8'), "id": user.id})
    else:
        return make_response((jsonify({"code": 401,
                                      "msg": "Authorization Failed"}), 401))


@auth.route('/oauth/token', methods=['POST'])
def create_token():
    # get request type. User or Service token?
    data = request.get_json()
    if data is None:
        return make_response(jsonify({"code": 400, "msg": "bad request"}), 400)

    request_type = data['request_type']

    if request_type == 'ccg':
        client_id = data['client_id']
        client_secret = data['client_secret']
        if not is_authorized_app(client_id, client_secret):
            return make_response(jsonify({"code": 401, "msg": "Could not verify"}), 401)
        service_token = create_service_token(data)
        return jsonify({"access_token": service_token.decode('UTF-8'), "msg": "success"})

    elif request_type == 'acg':
        user_token = create_user_token(data)
        return jsonify({"access_token": user_token.decode('UTF-8'), "msg": "success"})

    else:
        return make_response(jsonify({"code": 400, "msg": "invalid grant type"}), 400)
