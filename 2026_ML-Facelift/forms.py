from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from flask_wtf.file import FileField, FileAllowed, FileRequired
from datetime import date

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(),
        Length(min=3, max=80)
    ])
    displayName = StringField('Display Name', validators=[
        DataRequired(),
        Length(min=1, max=100)
    ])
    email = StringField('Email', validators=[
        DataRequired(),
        Email()
    ])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=10)
    ])
    confirmPassword = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Register')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class AddProgressForm(FlaskForm):
    date = DateField('Date', validators=[DataRequired()], default=date.today)
    title = StringField('Title', validators=[
        DataRequired(),
        Length(max=100)
    ])
    details = TextAreaField('Details', validators=[DataRequired()])
    image = FileField('Upload Supporting Image (optional)', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Only image files are allowed!')
    ])
    submit = SubmitField('Save Progress Log')

class QuoteForm(FlaskForm):
    tickerName = StringField('Ticker Name', validators=[DataRequired()])
    submit = SubmitField('Search')