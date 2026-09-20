import os

from flask import Flask, jsonify, render_template

app = Flask(__name__)

@app.route("/")
def main_window():
    return render_template("polyglot_academy.html")



@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/health")
def health():
    """Liveness for Docker/Caddy: the process answers. Nothing else to check - the site is stateless."""
    return jsonify(status="ok")


if __name__ == "__main__":
    # Development only. In production gunicorn imports `app` from this module (see Dockerfile).
    app.run(host=os.environ.get("HOST", "127.0.0.1"),
            port=int(os.environ.get("PORT", "5000")),
            debug=os.environ.get("FLASK_DEBUG", "1") == "1")
