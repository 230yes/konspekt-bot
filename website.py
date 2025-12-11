"""
ПРОСТОЙ website.py который точно работает
"""
import os
from flask import Flask, render_template, jsonify

# Создаем приложение
app = Flask(__name__)

# Главная страница
@app.route('/')
def home():
    return "Konspekt Bot работает! Откройте @Konspekt_help_bot в Telegram"

# Health check для Render
@app.route('/health')
def health():
    return jsonify({"status": "ok", "message": "Website is running"})

# Запуск
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
