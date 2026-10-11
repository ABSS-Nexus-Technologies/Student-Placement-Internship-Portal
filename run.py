import os
from app import create_app, db

app = create_app()

@app.cli.command("init-db")
def init_db():
    """Initializes database schema."""
    with app.app_context():
        db.create_all()
        print("Database schema initialized successfully.")

@app.cli.command("seed")
def seed():
    """Runs data seeder."""
    from seeds.seed_data import seed_database
    seed_database()

if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() in ['true', '1', 'on']
    app.run(host=host, port=port, debug=debug)
