import os


class Config:
    """
    Конфигурация приложения.

    - В Docker берётся DATABASE_URL из docker-compose.yml
    - Локально (если DATABASE_URL нет) используется SQLite
    """

    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///local.db")

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Секретный ключ (для сессий, форм и т.п.)
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
