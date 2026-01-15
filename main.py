from flask import Flask, render_template

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




if __name__ == "__main__":
    app.run(debug=True)

