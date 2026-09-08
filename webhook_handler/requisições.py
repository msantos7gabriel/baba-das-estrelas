import requests
import base64
from os import environ

# Fazer com decoradores


# Envio das mensagens
def requisicao_post(mensagem, grupo_id):
    # Prepara a URL e a Autenticação
    url_api = f"http://localhost:8080/message/sendText/{environ.get('INSTANCE_NAME')}"
    headers = {
        "apikey": str(environ.get('AUTHENTICATION_API_KEY')),
        "Content-Type": "application/json"
    }

    # Corpo da requisição com o número do grupo e a mensagem
    payload = {
        "number": grupo_id,
        "text": mensagem
    }

    # Requisição POST para enviar a mensagem de volta ao grupo
    try:
        requisição = requests.post(
            url_api, json=payload, headers=headers)
        if requisição.status_code == 200 or requisição.status_code == 201:
            print("Resposta enviada com sucesso!")
        else:
            print(
                f"Falha ao enviar a resposta. Status code: {requisição.status_code}, Resposta: {requisição.text}")
    except Exception as e:
        print(f"Erro ao tentar enviar a resposta: {e}")


# Envio de áudios
def requisicao_post_audio(media_name, grupo_id):
    url_api = (
        f"http://localhost:8080/message/sendMedia/"
        f"{environ.get('INSTANCE_NAME')}"
    )

    headers = {
        "apikey": str(environ.get("AUTHENTICATION_API_KEY")),
        "Content-Type": "application/json"
    }

    caminho = f"media/{media_name}"

    with open(caminho, "rb") as audio:
        audio_base64 = base64.b64encode(audio.read()).decode("utf-8")

    payload = {
        "number": grupo_id,
        "mediatype": "audio",
        "mimetype": "audio/mpeg",
        "media": audio_base64,
        "fileName": media_name
    }

    try:
        resposta = requests.post(
            url_api,
            json=payload,
            headers=headers
        )
        if resposta.status_code == 200 or resposta.status_code == 201:
            print("Resposta enviada com sucesso!")
        else:
            print(
                f"Falha ao enviar a resposta. Status code: {resposta.status_code}, Resposta: {resposta.text}")
    except Exception as e:
        print(f"\nErro ao tentar enviar a resposta: {e}")
