"""Dash application entry point."""

from pages.scr002_customer360 import app, server


if __name__ == "__main__":
    app.run(debug=False)
