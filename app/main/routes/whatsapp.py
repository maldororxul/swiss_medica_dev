""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'
from flask import request, jsonify
from app.main import bp
from config import Config


@bp.route('/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    if request.method == 'GET':
        # Handle the verification request from Meta
        params = request.args
        print(params)
        if 'hub.verify_token' in params and params['hub.verify_token'] == Config.META_WHATSAPP_TOKEN:
            print('good?')
            return params['hub.challenge']
        else:
            return jsonify({'error': 'Invalid Verify Token'}), 403
    elif request.method == 'POST':
        data = request.json
        # Process the incoming WhatsApp message or notification here
        # You can also send messages back to the user using the WhatsApp API
        # For example, you can use Twilio API for this purpose
        return jsonify({'status': 'success'})
