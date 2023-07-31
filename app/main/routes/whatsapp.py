""" Маршруты для работы WhatsApp-ботов """
__author__ = 'ke.mizonov'
import requests
from flask import request, jsonify
from app.main import bp
from config import Config


def reply(msg: str, number: str):
    res = requests.post(
        url='https://graph.facebook.com/v13.0/PHONE_NUMBER_ID/messages',
        headers={'Authorization': f"Bearer {Config.META_SYSTEM_USER_TOKEN}"},
        json={
            'messaging_product': 'whatsapp',
            'to': number,
            'type': 'text',
            "text": {
                "body": msg
            }
        }
    )
    print(res.text)


@bp.route('/whatsapp', methods=['GET', 'POST'])
def whatsapp_webhook():
    # see https://www.pragnakalp.com/automate-messages-using-whatsapp-business-api-flask-part-1/
    #   https://developers.facebook.com/blog/post/2022/10/24/sending-messages-with-whatsapp-in-your-python-applications/
    if request.method == 'GET':
        # Handle the verification request from Meta
        params = request.args
        if 'hub.verify_token' in params and params['hub.verify_token'] == Config.META_WHATSAPP_TOKEN:
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
