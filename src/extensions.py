from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# 여기서 만든 db 객체를 온 동네에서 가져다 씁니다.
db = SQLAlchemy()
migrate = Migrate()