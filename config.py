import os


class Config:
  # Clé secrète pour sécuriser les sessions et les formulaires
  SECRET_KEY = os.environ.get('SECRET_KEY') or 'boya-jc-secure-secret-key-2026'

  # Configuration dynamique de la base de données (PostgreSQL sur Render, SQLite en local)
  database_url = os.environ.get('DATABASE_URL')
  if database_url:
    if database_url.startswith('postgres://'):
      database_url = database_url.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_DATABASE_URI = database_url
  else:
    SQLALCHEMY_DATABASE_URI = 'sqlite:///boya_jc.db'

  SQLALCHEMY_TRACK_MODIFICATIONS = False