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


def requisicao_delete_mensagem(
    grupo_id, mensagem_id, from_me=False, participante_id=None
):
    url_api = (
        f"http://localhost:8080/chat/deleteMessageForEveryone/"
        f"{environ.get('INSTANCE_NAME')}"
    )
    headers = {
        "apikey": str(environ.get("AUTHENTICATION_API_KEY")),
        "Content-Type": "application/json"
    }
    payload = {
        "id": mensagem_id,
        "remoteJid": grupo_id,
        "fromMe": from_me
    }
    if not from_me:
        if not participante_id:
            print(
                "Falha ao apagar mensagem de terceiro: "
                "'participante_id' não fornecido."
            )
            return None
        payload["participant"] = participante_id

    try:
        resposta = requests.delete(url_api, json=payload, headers=headers)
        if resposta.status_code in (200, 201, 204):
            print("Mensagem apagada com sucesso!")
        else:
            print(
                f"Falha ao apagar a mensagem. Status code: "
                f"{resposta.status_code}, Resposta: {resposta.text}"
            )
        return resposta
    except requests.RequestException as e:
        print(f"Erro ao tentar apagar a mensagem: {e}")
