""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'
from typing import Optional
import requests
from flask import request, jsonify
from app.main import bp
from config import Config


def send_wahtsapp_message(number_to: str, number_id_from: str, template: Optional[str] = None, message: Optional[str] = None):
    if template:
        data = {
            'messaging_product': 'whatsapp',
            'to': number_to,
            'type': 'template',
            'template': template
        }
    elif message:
        data = {
            'messaging_product': 'whatsapp',
            'to': number_to,
            'type': 'text',
            "text": {
                "body": message
            }
        }
    else:
        return None
    headers = {
        'Authorization': f"Bearer {Config().meta_system_user_token}",
        'Content-Type': 'application/json'
    }
    res = requests.post(
        url=f'https://graph.facebook.com/v17.0/{number_id_from}/messages',
        headers=headers,
        json=data
    )
    print(res.text)


@bp.route('/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    # see https://www.pragnakalp.com/automate-messages-using-whatsapp-business-api-flask-part-1/
    #   https://developers.facebook.com/blog/post/2022/10/24/sending-messages-with-whatsapp-in-your-python-applications/
    if request.method == 'GET':
        # Handle the verification request from Meta
        params = request.args
        if 'hub.verify_token' in params and params['hub.verify_token'] == Config().meta_whatsapp_token:
            return params['hub.challenge'], 200
        else:
            return jsonify({'error': 'Invalid Verify Token'}), 403
    elif request.method == 'POST':
        data = request.get_json()
        try:
            print(data)
            if data['entry'][0]['changes'][0]['value']['messages'][0]['id']:
                pass
                # reply(msg="Thank you for the response.", number=)
        except:
            pass
        return '200 OK HTTPS.'


@bp.route('/whatsapp_remove', methods=['GET', 'POST'])
def whatsapp_remove():
    pass
