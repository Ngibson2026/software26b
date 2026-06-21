from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from flask_login import login_required, LoginManager, UserMixin, current_user, login_user, logout_user
import sqlite3
import logging  # library for logging security events
import bleach  # library for sanitisation of data
from email_validator import validate_email, EmailNotValidError
from zxcvbn import zxcvbn  # password rules
from forms import RegistrationForm, LoginForm, AddProgressForm, QuoteForm  # importing classes from forms file
from flask_wtf import FlaskForm  # library to allow use of wtforms
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField  # fields for forms
from wtforms.validators import DataRequired, Length, Email  # validati0on types within forms
from flask_wtf.csrf import CSRFProtect  # allowing CSRF protection
from contextlib import contextmanager
import yfinance as yf
import os
from dotenv import load_dotenv  # use more secure session key
from datetime import datetime
import plotly.express as px
import plotly.io as pio


#region init
app = Flask(__name__)
load_dotenv()  # loads .env file
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')  # For sessions and flash messages
if not app.config['SECRET_KEY']:
    raise ValueError("No FLASK_SECRET_KEY set in environment or .env file!")


# Enable CSRF Protection
csrf = CSRFProtect(app)

# Uploads folder
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create uploads folder if it doesn't exist

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Redirect to /login for unauthorized access
login_manager.login_message = 'Please log in to access this page'
login_manager.login_message_category = 'error'

# User class for Flask-Login
class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username
#endregion

#region subroutines
# run user input to remove dangerous content
def clean_input(s: str, allow_html: bool = False) -> str:
    # Strip dangerous content. allow_html=False removes all tags.
    s = s.strip()
    if allow_html:
        # Allow very limited formatting (adjust tags as needed)
        return bleach.clean(s, tags=['p', 'br', 'strong', 'em'], attributes={}, strip=True)
    else:
        # Remove all HTML
        return bleach.clean(s, tags=[], strip=True)
        
def clean_log_title(s: str) -> str:
    # Strip dangerous content. allow_html=False removes all tags.
    s = s.strip()
    # Remove all HTML
    cleaned = bleach.clean(s, tags=[], strip=True)
    return cleaned[:100]

def clean_log_details(s: str) -> str:
    # Strip dangerous content. allow_html=False removes all tags.
    s = s.strip()    
    # Allow very limited formatting (adjust tags as needed)
    return bleach.clean(s, tags=['p', 'br', 'strong', 'em', 'ul', 'ol', 'li', 'u'], attributes={}, strip=True)

# check if email is a vaild address instead of just a@b.com
def validate_email_strict(email: str) -> tuple[bool, str]:
    try:
        validate_email(email, check_deliverability=False)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)
    
# implement password rules    
def validate_password_strength(password: str) -> tuple[bool, str]:
    if len(password) < 10:
        return False, "Password must be at least 10 characters"    
    result = zxcvbn(password)
    if result['score'] < 3:
        warning = result['feedback']['warning'] or "Password is too weak"
        suggestions = " ".join(result['feedback']['suggestions'])
        return False, f"{warning} {suggestions}".strip()   
    return True, "Strong password"

# Load user from database
@login_manager.user_loader
def load_user(user_id):
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, username FROM Users WHERE id = ?',
                (user_id,)
            )
            user = cursor.fetchone()  # get the first record from query result

        if user:
            # create instance of user class
            return User(id=user['id'], username=user['username'])
        return None

    except Exception as e:
        # Log the error in development, but don't expose it to user
        print(f"Error loading user {user_id}: {e}")  # Replace with proper logging later
        return None

# Database connection function
@contextmanager
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    # to close the db after the processing is complete
    try:
        yield conn  # keep connection open while actively accessing db
    finally:  # when finished        
        conn.close()

def get_stock_info(ticker: str):
    if not ticker or len(ticker.strip()) < 1:  # if ticker name is too short
        return None, None, "Please enter a valid ticker symbol"
    
    ticker = ticker.upper().strip()  # convert to uppercase, remove any unwanted spaces

    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Current price -- get the first price found then exit loop
        current_price = None  # initialise current price
        for key in ['currentPrice', 'regularMarketPrice', 'price']:
            if info.get(key):
                current_price = info.get(key)
                break
        
        stock_data = {
            'ticker': ticker,
            'name': info.get('longName') or info.get('shortName') or f"{ticker} Stock",
            'current_price': round(current_price, 2) if current_price else None,
            'previous_close': round(info.get('regularMarketPreviousClose', 0), 2),
            'market_cap': info.get('marketCap'),
            'currency': info.get('currency', 'USD'),
            'summary': info.get('longBusinessSummary'),
            'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M")
            }

        # Get historical data for chart (last 3 months)
        hist = stock.history(period="5y")
        chart_data = None

        if not hist.empty:
            chart_data = {
                'dates': hist.index.strftime('%Y-%m-%d').tolist(),
                'close': hist['Close'].round(2).tolist()
            }

        return stock_data, chart_data, None

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None, None, f"Failed to fetch data for {ticker}. Please try again."

#endregion

@app.route('/')
@login_required
def index():
    # return 'Index page'
    return redirect(url_for('login'))

@app.route('/add_progress', methods=['GET', 'POST'])
@login_required
def add_progress():
    form = AddProgressForm()  # for prevention of CSRF

    if form.validate_on_submit():
        date_str = form.date.data.strftime('%Y-%m-%d')   # Convert date to string
        title = clean_log_title(form.title.data)  # input sanitisation
        details = clean_log_details(form.details.data)

        # Uploading images
        image_path = None  # initialising image_path
        if form.image.data and form.image.data.filename:
            file = form.image.data  # store image into variable
            print(f"DEBUG: File received - Filename: {file.filename}")
            print(f"DEBUG: File content type: {file.content_type}")

            filename = secure_filename(file.filename)  # run the filename through werkzeug
            unique_filename = f"user_{current_user.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"  # adding metadata to file name
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)  # set the file path with the folder so the app knows where to store the file

            try:
                # upload file to the server
                file.save(file_path)
                image_path = f"uploads/{unique_filename}"
                print(f"DEBUG: Image successfully saved to: {file_path}")
                print(f"DEBUG: image_path saved in DB will be: {image_path}")
            except Exception as e:
                print(f"ERROR saving image: {e}")
                flash(f'Failed to save image: {str(e)}', 'warning')
        else:
            print("DEBUG: No image file was uploaded or filename was empty")


        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO ProgressLogs (user_id, date, title, details, image_path) VALUES (?, ?, ?, ?, ?)",
                    (current_user.id, date_str, title, details, image_path)
                )
                conn.commit()

            flash('Progress log added successfully!', 'success')
            return redirect(url_for('view_progress'))

        except Exception as e:
            flash('An error occurred while saving your progress.', 'error')
            print(f"ERROR saving progress: {e}")
            import traceback
            traceback.print_exc()  # Print full traceback in console

    return render_template('addProgress.html', form=form, username=current_user.username)

@app.route('/buy_stock', methods=['POST'])
@login_required
def buy_stock():
    ticker = request.form.get('ticker', '').strip().upper()  # name of ticker with informtation
    shares = request.form.get('shares', type=int)  # number of shares to buy

    if not ticker or not shares or shares <= 0:  # checks for invalid data
        flash('Invalid ticker or number of shares.', 'error')
        return redirect(url_for('quote_stock'))

    # Get current price
    stock_data, _, error = get_stock_info(ticker)
    if error or not stock_data or not stock_data['current_price']:  # checking for invalid data
        flash('Could not fetch current price. Please try again.', 'error')
        return redirect(url_for('quote_stock'))

    price_per_share = stock_data['current_price']  # display current price
    total_cost = round(price_per_share * shares, 2)  # display total cost of shares

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get user's current cash balance
            cursor.execute("SELECT cash_balance FROM UserBalances WHERE user_id = ?", (current_user.id,))
            balance_row = cursor.fetchone()
            current_balance = balance_row['cash_balance'] if balance_row else 0.0

            if current_balance < total_cost:  # check for balance
                flash(f'Insufficient funds! You need ${total_cost:,.2f} but only have ${current_balance:,.2f}', 'error')
                return redirect(url_for('quote_stock'))

            # Update cash balance
            new_balance = round(current_balance - total_cost, 2)  # calculate new user balance
            cursor.execute(
                "UPDATE UserBalances SET cash_balance = ? WHERE user_id = ?",
                (new_balance, current_user.id)
            )

            # Update or insert into Portfolio
            cursor.execute("""
                INSERT INTO Portfolio (user_id, ticker, shares, average_buy_price)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, ticker) 
                DO UPDATE SET 
                    shares = shares + ?,
                    average_buy_price = ((average_buy_price * shares) + (? * ?)) / (shares + ?),
                    last_updated = CURRENT_TIMESTAMP
            """, (current_user.id, ticker, shares, price_per_share,
                  shares, price_per_share, shares, shares))

            # Record transaction
            cursor.execute("""
                INSERT INTO Transactions 
                (user_id, ticker, transaction_type, shares, price_per_share, total_amount)
                VALUES (?, ?, 'BUY', ?, ?, ?)
            """, (current_user.id, ticker, shares, price_per_share, total_cost))

            conn.commit()  

        flash(f'Successfully bought {shares} shares of {ticker} for ${total_cost:,.2f}', 'success')
        return redirect(url_for('quote_stock', ticker=ticker))   # Stay on same ticker

    except Exception as e:
        flash('An error occurred while processing your purchase.', 'error')
        print(f"Buy error: {e}")
        return redirect(url_for('quote_stock'))

@app.route('/dashboard')
@login_required
def dashboard():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT cash_balance FROM UserBalances WHERE user_id = ?", (current_user.id,))
            balance_row = cursor.fetchone()
            cash_balance = float(balance_row['cash_balance']) if balance_row else 0.0

            cursor.execute("""
                SELECT ticker, shares, average_buy_price
                FROM Portfolio 
                WHERE user_id = ?
                ORDER BY ticker
            """, (current_user.id,))
            holdings = cursor.fetchall()

        # First pass: Calculate market values and total portfolio value -- initialise variables
        enhanced_holdings = []
        portfolio_value = 0.0  
        total_unrealized_pnl = 0.0
        total_cost_basis = 0.0

        for holding in holdings:
            ticker = holding['ticker']
            shares = holding['shares']
            avg_buy_price = holding['average_buy_price']

            stock_data, _, error = get_stock_info(ticker)
            current_price = stock_data['current_price'] if stock_data and not error else None

            if current_price:
                market_value = round(shares * current_price, 2)
                unrealized_pnl = round((current_price - avg_buy_price) * shares, 2)
                cost_basis = round(avg_buy_price * shares, 2)

                portfolio_value += market_value
                total_unrealized_pnl += unrealized_pnl
                total_cost_basis += cost_basis

                enhanced_holdings.append({
                    'ticker': ticker,
                    'shares': shares,
                    'avg_buy_price': round(avg_buy_price, 2),
                    'current_price': round(current_price, 2),
                    'market_value': market_value,
                    'unrealized_pnl': unrealized_pnl,
                    'pnl_percent': round(((current_price - avg_buy_price) / avg_buy_price * 100), 2) if avg_buy_price > 0 else 0,
                    'weight': 0  # placeholder
                })
            else:
                enhanced_holdings.append({
                    'ticker': ticker,
                    'shares': shares,
                    'avg_buy_price': round(avg_buy_price, 2),
                    'current_price': None,
                    'market_value': None,
                    'unrealized_pnl': None,
                    'pnl_percent': None,
                    'weight': 0
                })

        total_portfolio_value = round(cash_balance + portfolio_value, 2)
        overall_return = round(((portfolio_value - total_cost_basis) / total_cost_basis * 100),
                               2) if total_cost_basis > 0 else 0

        # Second pass: Calculate correct weights
        if portfolio_value > 0:
            for holding in enhanced_holdings:
                if holding['market_value']:
                    holding['weight'] = round((holding['market_value'] / portfolio_value) * 100, 1)

        # Prepare data for Plotly pie chart
        tickers_for_pie = [h['ticker'] for h in enhanced_holdings if h['market_value']]
        weights_for_pie = [h['weight'] for h in enhanced_holdings if h['market_value']]

        # Create Plotly Pie Chart
        # import plotly.express as px
        # import plotly.io as pio

        allocation_chart = ""
        if tickers_for_pie and weights_for_pie:
            fig = px.pie(
                names=tickers_for_pie,
                values=weights_for_pie,
                title="Asset Allocation by Market Value",
                hole=0.1
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(height=450, showlegend=True)
            allocation_chart = pio.to_html(fig, full_html=False, include_plotlyjs='cdn')

        # Top Gainer and Top Loser
        top_gainer = max(enhanced_holdings, key=lambda x: x.get('unrealized_pnl') or -999999, default=None)
        top_loser = min(enhanced_holdings, key=lambda x: x.get('unrealized_pnl') or 999999, default=None)

        return render_template('dashboard.html',
                               cash_balance=round(cash_balance, 2),
                               portfolio_value=round(portfolio_value, 2),
                               total_portfolio_value=total_portfolio_value,
                               total_unrealized_pnl=round(total_unrealized_pnl, 2),
                               overall_return=overall_return,
                               total_invested=round(total_cost_basis, 2),
                               holdings=enhanced_holdings,
                               top_gainer=top_gainer,
                               top_loser=top_loser,
                               allocation_chart=allocation_chart)

    except Exception as e:
        print(f"Dashboard error: {e}")
        import traceback
        traceback.print_exc()
        flash('Error loading dashboard.', 'error')        
        return render_template(
                'dashboard.html',
                cash_balance=0,
                portfolio_value=0,
                total_portfolio_value=0,
                total_unrealized_pnl=0,
                overall_return=0,
                total_invested=0,
                holdings=[],
                top_gainer=None,
                top_loser=None,
                allocation_chart=""
            )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:  # if user logged in, send to dashboard
        return redirect(url_for('dashboard'))
    
    form = LoginForm()  # reference to the login form class - creating a loginform object

    if form.validate_on_submit():  # run the following code if the data in it is valid
        username = form.username.data.strip()  # cleaning the username and storing it
        password = form.password.data

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                # check if user exists - if so return id, username, hashed pw
                cursor.execute( 
                    "SELECT id, username, hashed_password FROM Users WHERE username = ?",
                    (username,)
                )
                user_row = cursor.fetchone()  # storing the first result

            # IF not null, and passwords match
            if user_row and check_password_hash(user_row['hashed_password'], password):
                user = User(id=user_row['id'], username=user_row['username'])
                login_user(user)
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password.', 'error')

        except Exception as e:
            flash('An error occurred during login. Please try again.', 'error')

    return render_template('login.html', form=form)

@app.route('/logoff')
@login_required
def logoff():
    '''if 'user_id' not in session:
        flash('You need to be logged in to view this content.', 'error')
    else:'''
    # session.pop('user_id', None)
    logout_user()
    flash('You have successfully logged out.', 'success')
    return redirect(url_for('login'))
    # add a link to base.html to run this route -- in the navbar

@app.route('/quote_stock', methods=['GET', 'POST'])  # added the methods statement to fix the 405 error
@login_required
def quote_stock():
    form = QuoteForm()
    
    stock_data = None
    chart_data = None
    error = None
    tickerName = None

    if form.validate_on_submit():  # moved the if check after initialising variables to stop the i dont know that variable error
        tickerName = request.form.get('tickerName', '').strip()

        if tickerName:
            stock_data, chart_data, error = get_stock_info(tickerName)
        else:
            error = "Please enter a stock ticker symbol (e.g. BHP.AX)"

    return render_template('quote_stock.html', form=form, stock_data=stock_data, chart_data=chart_data, error=error, tickerName=tickerName, username=current_user.username)



@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = RegistrationForm()

    if form.validate_on_submit():
        username = clean_input(form.username.data)
        displayName = clean_input(form.displayName.data)
        email = clean_input(form.email.data)
        password = form.password.data

        try:
            with get_db_connection() as conn:
                cursor = conn.cursor()
                hashed_password = generate_password_hash(password)

                cursor.execute(
                    """INSERT INTO Users (username, hashed_password, email, display_name)
                       VALUES (?, ?, ?, ?)""",
                    (username, hashed_password, email, displayName)
                )
                conn.commit()  # finalise data in table / save data from query

                # automatically log new user in
                cursor.execute("SELECT id, username FROM Users WHERE username = ?", (username,))
                user_row = cursor.fetchone()

            if user_row:
                new_user = User(id=user_row['id'], username=user_row['username'])
                login_user(new_user)
                flash('Registration successful! Welcome!', 'success')
                return redirect(url_for('dashboard'))

        except sqlite3.IntegrityError:
            flash('Username or email already exists.', 'error')
        except Exception as e:
            flash('An unexpected error occurred. Please try again.', 'error')

    return render_template('register.html', form=form)

@app.route('/sell_stock', methods=['POST'])
@login_required
def sell_stock():
    ticker = request.form.get('ticker', '').strip().upper()
    shares_to_sell = request.form.get('shares', type=int)

    if not ticker or not shares_to_sell or shares_to_sell < 1:
        flash('Invalid ticker or number of shares.', 'error')
        return redirect(url_for('dashboard'))

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # Get current holding
            cursor.execute("""
                SELECT shares, average_buy_price 
                FROM Portfolio 
                WHERE user_id = ? AND ticker = ?
            """, (current_user.id, ticker))
            holding = cursor.fetchone()

            if not holding or holding['shares'] < shares_to_sell:
                flash(f'You only own {holding["shares"] if holding else 0} shares of {ticker}. Cannot sell {shares_to_sell} shares.', 'error')
                return redirect(url_for('dashboard'))

            avg_buy_price = holding['average_buy_price']

            # Get current market price
            stock_data, _, error = get_stock_info(ticker)
            if error or not stock_data or not stock_data.get('current_price'):
                flash('Could not fetch current price. Please try again later.', 'error')
                return redirect(url_for('dashboard'))

            current_price = stock_data['current_price']
            total_proceeds = round(current_price * shares_to_sell, 2)

            # Update cash balance
            cursor.execute("SELECT cash_balance FROM UserBalances WHERE user_id = ?", (current_user.id,))
            balance_row = cursor.fetchone()
            current_balance = float(balance_row['cash_balance']) if balance_row else 0.0
            new_balance = round(current_balance + total_proceeds, 2)

            cursor.execute(
                "UPDATE UserBalances SET cash_balance = ? WHERE user_id = ?",
                (new_balance, current_user.id)
            )

            # Update portfolio
            remaining_shares = holding['shares'] - shares_to_sell
            if remaining_shares > 0:
                cursor.execute("""
                    UPDATE Portfolio 
                    SET shares = ?, last_updated = CURRENT_TIMESTAMP 
                    WHERE user_id = ? AND ticker = ?
                """, (remaining_shares, current_user.id, ticker))
            else:
                cursor.execute("DELETE FROM Portfolio WHERE user_id = ? AND ticker = ?",
                             (current_user.id, ticker))

            # Record transaction
            cursor.execute("""
                INSERT INTO Transactions 
                (user_id, ticker, transaction_type, shares, price_per_share, total_amount)
                VALUES (?, ?, 'SELL', ?, ?, ?)
            """, (current_user.id, ticker, shares_to_sell, current_price, total_proceeds))

            conn.commit()

        flash(f'Successfully sold {shares_to_sell} shares of {ticker} for ${total_proceeds:,.2f}', 'success')

    except Exception as e:
        flash('An error occurred while selling the stock.', 'error')
        print(f"Sell error: {e}")
        import traceback
        traceback.print_exc()

    return redirect(url_for('dashboard'))


@app.route('/transactions')
@login_required
def transactions():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT t.id,
                                  t.ticker,
                                  t.transaction_type,
                                  t.shares,
                                  t.price_per_share,
                                  t.total_amount,
                                  t.timestamp,
                                  t.user_id
                           FROM Transactions t
                           WHERE t.user_id = ?
                           ORDER BY t.timestamp DESC
                           """, (current_user.id,))

            transactions = cursor.fetchall()

        return render_template('transactions.html',
                               transactions=transactions,
                               username=current_user.username)

    except Exception as e:
        print(f"Transactions error: {e}")
        flash('Error loading transaction history.', 'error')
        return redirect(url_for('dashboard'))

@app.route('/view_progress', methods=['GET', 'POST'])
@login_required
def view_progress():
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT id, date, title, details, image_path
                   FROM ProgressLogs
                   WHERE user_id = ?
                   ORDER BY date DESC, id DESC""",  # Newer entries first
                (current_user.id,)
            )
            posts = cursor.fetchall()

        return render_template('viewProgress.html', posts=posts, username=current_user.username)

    except Exception as e:
        flash('Error loading your progress logs.', 'error')
        print(f"Error loading progress: {e}")

if __name__ == '__main__':
    app.run(debug=True)
