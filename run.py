"""Application runner script."""
from app.app import app, initialize_defaults

initialize_defaults()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
