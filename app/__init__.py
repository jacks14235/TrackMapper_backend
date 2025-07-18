# app/__init__.py
import os
from flask import Flask
from .extensions import db
from .routes import bp

def create_app():
    app = Flask(__name__)
    # load config.py (or environment vars)
    app.config.from_pyfile('../config.py')
    # ensure upload folder exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # initialize extensions
    db.init_app(app)

    # register blueprints
    app.register_blueprint(bp)

    # create tables on first run
    with app.app_context():
        db.create_all()

    return app
