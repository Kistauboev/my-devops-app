from flask import Flask
import time

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Hello DevOps World!</h1><p>Version: 2.0.0 - Auto Deployed!</p>'

@app.route('/health')
def health():
    return {'status': 'healthy', 'timestamp': time.time()}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)