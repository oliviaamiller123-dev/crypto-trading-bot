from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return "Crypto Trading Bot is Running Successfully!"

if __name__ == '__main__':
    app.run()
