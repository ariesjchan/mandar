import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    COINS_PH_API_KEY = os.getenv('COINS_PH_API_KEY')
    COINS_PH_API_SECRET = os.getenv('COINS_PH_API_SECRET')
