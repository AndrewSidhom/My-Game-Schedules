from flask import Flask
from config import DevConfig, Config


app = Flask(__name__)
app.config.from_object(DevConfig)


from auth import auth, setup_connector
app.register_blueprint(auth)


@app.route('/')
def hello_world():
    return 'Hello World!'


if __name__ == '__main__':
    setup_connector(app)
    app.run()
