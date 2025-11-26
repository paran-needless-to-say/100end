# src/__init__.py

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 1. 전역에서 사용할 db와 migrate 객체 생성
# (다른 파일에서 'from src import db'로 가져다 쓰게 됩니다)
db = SQLAlchemy()
migrate = Migrate()

def create_app():
    # 2. Flask 애플리케이션 생성
    app = Flask(__name__)

    # --- [설정 구역] ---
    # 보안 키 (실제 배포시는 복잡하게 설정해야 함)
    app.config['SECRET_KEY'] = 'my-secret-key'
    # 데이터베이스 파일 경로 (프로젝트 폴더에 project.db 파일이 생깁니다)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # 3. 확장 프로그램 연결 (db와 앱을 연결)
    db.init_app(app)
    migrate.init_app(app, db)

    # 4. 블루프린트 등록 (우리가 만든 기능 연결!)
    # visualizing_data 폴더의 bp를 가져와서 앱에 등록합니다.
    from src.visualizing_data import bp as visualizing_bp
    app.register_blueprint(visualizing_bp)

    return app