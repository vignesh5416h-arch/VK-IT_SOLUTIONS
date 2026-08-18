from app import app, db, User


def test_owner_is_initialized_on_app_startup():
    with app.app_context():
        db.create_all()
        owners = User.query.filter_by(role="owner").all()
        assert len(owners) >= 1
