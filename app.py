from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY

# intializing flask app
app = Flask(__name__)

# configuring the application
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY

# initializing the database
db = SQLAlchemy(app)

# test
@app.route('/')
def home():
    return "Mock Trading Platform is up and running!"

# run the app
if __name__ == "__main__":
    app.run(debug=True)