from flask import Flask, render_template, jsonify
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'default-secret-key-12345')

@app.route('/')
def index():
    """Главная страница"""
    return render_template('index.html', section='home')

@app.route('/about')
def about():
    """Страница о боте"""
    return render_template('index.html', section='about')

@app.route('/instructions')
def instructions():
    """Инструкция"""
    return render_template('index.html', section='instructions')

@app.route('/formats')
def formats():
    """Форматы"""
    return render_template('index.html', section='formats')

@app.route('/health')
def health():
    """Health check для Render"""
    return jsonify({
        'status': 'ok',
        'service': 'konspekt-bot',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/status')
def api_status():
    """API статуса"""
    return jsonify({
        'name': 'Konspekt Help Bot',
        'version': '1.0.0',
        'status': 'running',
        'telegram': '@Konspekt_help_bot'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
