from config import SQLALCHEMY_DATABASE_URI, SQLALCHEMY_TRACK_MODIFICATIONS, SECRET_KEY
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# intializing flask app
app = Flask(__name__)

# configuring the application
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = SQLALCHEMY_TRACK_MODIFICATIONS
app.config['SECRET_KEY'] = SECRET_KEY

from models import db, bcrypt, User, PortfolioHolding

# initializing extensions
db.init_app(app)
bcrypt.init_app(app)

# test
@app.route('/')
def home():
    return "Mock Trading Platform is up and running!"

# setting up login manager
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        # checking if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email is already registered', 'danger')
            return redirect(url_for('register'))
        
        # create new user and add to database
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

# logging in
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        # check if user exists
        if user and user.check_password(password):
            login_user(user)
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        flash('Invalid email or password', 'danger')
    
    return render_template('login.html')

# logging out
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

import requests
from flask import jsonify

# helper function to fetch stock price
def get_stock_price(symbol):
    API_KEY = 'API_KEY'
    url = f'https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval=1min&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()

    # extracting latest price
    try:
        time_series = data['Time Series (Daily)']
        dates = []
        prices = []
        for date, daily_data in time_series.items():
            dates.append(date)
            prices.append(float(daily_data['4. close']))
        return dates, prices
    except (KeyError, IndexError):
        return [], []

@app.route('/buy', methods=['POST'])
@login_required
def buy():
    symbol = request.form.get('symbol')
    quantity = int(request.form.get('quantity'))

    # get current stock price
    price = get_stock_price(symbol)
    if price is None:
        flash('Invalid stock symbol or unable to fetch price', 'danger')
        return redirect(url_for('portfolio'))
    
    total_cost = price * quantity
    user = current_user

    # check if user has enough balance
    if user.balance < total_cost:
        flash('Insufficient balance to complete the purchase', 'danger')
        return redirect(url_for('portfolio'))
    
    # update user balance and portfolio
    user.balance -= total_cost
    holding = PortfolioHolding.query.filter_by(user_id=user.id, symbol=symbol).first()

    if holding:
        holding.quantity += quantity
    else:
        new_holding = PortfolioHolding(user_id=user.id, symbol=symbol, quantity=quantity, purchase_price=price)
        db.session.add(new_holding)
    
    db.session.commit()
    flash(f'Successfully bought {quantity} share of {symbol}', 'success')
    
    return redirect(url_for('portfolio'))

@app.route('/portfolio')
@login_required
def portfolio():
    user = current_user
    holdings = PortfolioHolding.query.filter_by(user_id=user.id).all()
    return render_template('portfolio.html', user=user, holdings=holdings)

@app.route('/sell', methods=['POST'])
@login_required
def sell():
    symbol = request.form.get('symbol')
    quantity = int(request.form.get('quantity'))

    # fetch current stock price
    price = get_stock_price(symbol)
    if price is None:
        flash('Invalid stock symbol or unable to fetch price', 'danger')
        return redirect(url_for('portfolio'))
    
    user = current_user
    holding = PortfolioHolding.query.filter_by(user_id=user.id, symbol=symbol).first()

    # check if user owns the stock and has enough quantity to sell
    if not holding or holding.quantity < quantity:
        flash('Insufficient shares to complete the sale', 'danger')
        return redirect(url_for('portfolio'))
    
    # calculate sale proceeds and update user's balance
    total_sale_value = price * quantity
    user.balance += total_sale_value
    holding.quantity -= quantity

    # remove the holding if quantity == 0
    if holding.quantity == 0:
        db.session.delete(holding)
    
    db.session.commit()
    flash(f'Successfully sold {quantity} shares of {symbol}', 'success')
    return redirect(url_for('portfolio'))

@app.route('/price-history/<symbol>')
@login_required
def price_history(symbol):
    dates, prices = get_stock_price(symbol)
    if not dates:
        flash('Unable to retrieve price history', 'danger')
        return redirect(url_for('portfolio'))
    
    # plotly graph
    import plotly.graph_objs as go
    fig = go.Figure(data=[go.Scatter(x=dates, y=prices, mode='lines', name=symbol)])
    fig.update_layout(title=f'Price history for {symbol}', xaxis_title='Date', yaxis_title='Price (USD)')
    graph_html = fig.to_html(full_html=False)

    return render_template('price_history.html', symbol=symbol, graph_html=graph_html)

# debugger
if __name__ == "__main__":
    app.run(debug=True)
