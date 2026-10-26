from flask import Flask, request, redirect, url_for, render_template, flash, session, jsonify, send_from_directory, send_file
app = Flask(__name__)

@app.route('/')
def index():
    return render_template('register.html')

@app.route('/registro')
def registro():
    return render_template('register.html')

@app.route('/login')
def login():
    return render_template('register.html')

@app.route('/')
def nuevo():
    return render_template('nueva.html')

@app.route('/')
def index():
    return render_template('editar.html')



if __name__ == "__main__":
    app.run(debug=True)





