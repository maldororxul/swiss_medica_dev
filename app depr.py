"""
Дать права пользователю:
GRANT ALL ON SCHEMA swissmedica TO swissmedica
https://www.youtube.com/watch?v=T_Jp2X9owQk
"""
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

load_dotenv()  # load environment variables

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
db = SQLAlchemy(app)


if __name__ == '__main__':
    app.run()
