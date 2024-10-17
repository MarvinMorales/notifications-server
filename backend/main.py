import json
import requests
from requests.exceptions import ConnectionError, HTTPError
from flask_cors import CORS, cross_origin
from flask import Flask, request, jsonify
from exponent_server_sdk import (
    PushClient,
    PushMessage,
    PushServerError,
    PushTicketError,
)

# Usar este modulo de Python para gestionar las web push
from pywebpush import webpush, WebPushException

app = Flask(__name__)

CORS(app)

# Crear las VAPID keys usando el modulo de NPM web-push
# https://www.npmjs.com/package/web-push
# Instalarlo y crear las keys usando la linea de comando
# Instalar -> npm install web-push -g (Esto lo instala globalmente)
# Crear las VAPID keys usando -> web-push generate-vapid-keys
# Se mostraran las VPID keys en la terminal, copiarlas y pegarlas como se muestra abajo
VAPID_PRIVATE_KEY = "vp6ItkXv7JNLw-0g0W9V1HMZbs8RQhJVof6Ad1Jw0Iw"
VAPID_PUBLIC_KEY = "BN3MHTt-j8nKyuBXN0oZ-33vNprwK_ukhornL4PNTfTHgPDMV8BYvyW3v-Xo6ttzQxIfjNOcwr1DPvQzcYLU_yA"

# Estoy usando esta lista para almacenar a los usuarios suscritos
# Puedes manejarlo como gustes, pero lo ideal es manjeralo con bases de datos
# Se debe guardar el objeto (diccionario) de la suscripcion para cada usuario que se suscriba
subscriptions_list = []
push_tokens = []
clients = {}

# Esta funcion la uso para crear y retornar el payload que voy a enviar en la notificacion
def send_notification_data(name: str, id: str):
    return {
        "title": f"{name}, tenemos una encuesta para ti",
        "survey_id": id,
        "body": "Lllena esta encuesta y gana 2000 puntos que puedes canjear por tarjetas de regalo!"
    }

# Esta funcion la uso para almacenar al usuario suscrito
# Almaceno solo uno de acuerdo al nombre "user" es decir, si recibo una notificacion con
# el mismo "user", esa nueva suscripcion reemplazara a la ya existente en la lista "subscriptions_list"
def store_subscription(subscription_data):
    global subscriptions_list
    # Extraer el 'user' del diccionario recibido
    user = subscription_data['user']
    # Verificar si el usuario ya existe en la lista
    user_exists = False
    for i, sub in enumerate(subscriptions_list):
        if sub['user'] == user:
            # Si el usuario ya existe, actualizar su suscripción
            subscriptions_list[i] = subscription_data
            user_exists = True
            break

    # Si el usuario no existe, agregarlo a la lista
    if not user_exists:
        subscriptions_list.append(subscription_data)


# Esta funcion la uso para obtener el diccionario de la suscripcion de un usuario especifico
# El usuario almacenado en la "subscriptions_list" seria asi:
"""
    {
        "user": "Marvin",
        "subscription": {
            // Aqui irian todas las demas keys del objet
            // de la suscripcion
        }
    }
"""
# Entonces cuando quiero obtener SOLO el objeto de la suscripcion de un usuario, 
# uso esta funcion para filtrar por "user" y sacar solo la key "subscription"
def get_subscription_by_user(user: str):
    global subscriptions_list
    # Buscar en la lista el usuario correspondiente
    for sub in subscriptions_list:
        if sub['user'] == user:
            return sub
    return None

# Esta funcion sirve para saber qcual es la URL del motor de navegador que va a manejar la notificacion
# Cada navegador tiene su propia URL
def get_vapid_audience(endpoint):
    if "mozilla" in endpoint:
        return "https://updates.push.services.mozilla.com"
    elif "googleapis" in endpoint:
        return "https://fcm.googleapis.com"
    else:
        raise ValueError("Navegador no soportado")

# Ruta para testear si el servidor esta levantado
# Ruta para mostrar la lista "subscriptions_list"
# Como es un GET, puede ejecutar esta URL en el navegador y mostrara la lista 
@app.route('/test', methods=["GET"])
@cross_origin(allow_headers=["Content-Type"])
def testing_route():
    return jsonify({ 
        "working": subscriptions_list, 
        "android": push_tokens,
        "nodes": clients
    }), 200


# Ruta para suscribir a un usuario a las notificaciones
@app.route('/subscription', methods=["POST"])
@cross_origin(allow_headers=["Content-Type"])
def subscription_route():
    subscription_info = request.get_json()
    print("Subscription ->", subscription_info)
    store_subscription(subscription_info)
    return jsonify({"status": "Subscription received"}), 201


# Ruta para enviar notificaciones a un usuario especifico
"""
Es un POST y Recibe este payload:
    {
        "user": "Marvin",
        "id": "4ab56ceb6aa"
    }
"""
@app.route('/send-notification', methods=['POST'])
@cross_origin(allow_headers=["Content-Type"])
def send_notification():
    user_name = request.get_json()
    # Uso la funcion "get_subscription_by_user" que esta declarada arriba 
    required_user = get_subscription_by_user(user_name["user"])
    # Dentro del objeto de la suscripcion viene una key "endpoint"
    # Este "endpoint" es el que decia que cada navegador lo usa para gestionar el envio de notificaciones
    endpoint = required_user["subscription"]["endpoint"]
    try:
        # Aqui uso "webpush" de python para enviar la notificacion
        webpush(
            data=json.dumps(send_notification_data(user_name["user"], user_name["id"])),
            # Aqui debo pasar SOLO el objeto "subscription" 
            subscription_info=required_user["subscription"],
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={ 
                "sub": "mailto:tu-email@dominio.com",
                "aud": get_vapid_audience(endpoint)
            },
        )
        return jsonify({"status": "Notification sent"}), 200
    except WebPushException as ex:
        print("WebPush Error: {}", repr(ex))
        return jsonify({"status": "Error sending notification", "detail": str(ex)}), 500
    


# Save data from Android device    
@app.route('/save-push-token', methods=['POST'])
@cross_origin(allow_headers=["Content-Type"])
def save_data_from_android():
    android_device = request.get_json()
    push_tokens.append(android_device)
    return jsonify({
        "success": True,
        "error": None,
        "data": { "status": "Subscription received" }
    }), 200



@app.route('/mobile/send-push-notification', methods=["POST"])
@cross_origin(allow_headers=["Content-Type"])
def send_push_message():
    try:
        data_retrieved = request.get_json()
        print("Datos recibidos:", data_retrieved)
        
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer LDh0tWeqUOwAfAY14PXLw6c9Jn8sS-YOCdlejkju",
                "accept": "application/json",
                "accept-encoding": "gzip, deflate",
                "content-type": "application/json",
            }
        )

        response = PushClient(session=session).publish(
            PushMessage(
                to=data_retrieved["token"],
                title=data_retrieved.get("title", ""),  # Título de la notificación
                body=data_retrieved["message"],
                data=data_retrieved["extra"]
            )
        )

        print("Respuesta del servidor:", response)
        return jsonify({"status": "success", "response": str(response)}), 200

    except PushServerError as exc:
        error_detail = f"There was an error: {exc}"
        print(error_detail)
        # Si exc tiene un atributo `response`, se puede registrar el contenido
        if hasattr(exc, 'response') and exc.response is not None:
            error_response = exc.response.json() if exc.response.content else {}
            error_detail += f", details: {error_response}"
        
        return jsonify({"status": "error", "message": "Request failed", "details": error_detail}), 500

    except Exception as e:
        error_detail = f"Unexpected error: {e}"
        print(error_detail)
        return jsonify({"status": "error", "message": "Unexpected error occurred", "details": error_detail}), 500



# Ruta para registrar clientes y obtener IP y puerto de otro cliente
@app.route('/register-nat', methods=['POST'])
def register():
    data = request.get_json()
    
    # Datos del cliente que se está registrando
    client_id = data['client_id']
    client_ip = data['ip']
    client_port = data['port']
    
    # Almacenar IP y puerto del cliente
    clients[client_id] = {
        'ip': client_ip,
        'port': client_port
    }

    # Aquí asumimos que hay otro cliente ya registrado, por simplicidad
    peer_id = 'peer' if client_id == 'client' else 'client'
    
    if peer_id in clients:
        peer_info = clients[peer_id]
        return jsonify({
            'peer_ip': peer_info['ip'],
            'peer_port': peer_info['port']
        }), 200
    else:
        # Aquí puedes retornar la IP y puerto de este cliente para que pueda guardar su información.
        return jsonify({
            'message': 'Esperando al otro peer...',
            'your_ip': client_ip,
            'your_port': client_port
        }), 200


if __name__ == '__main__':
    app.run(debug=True)