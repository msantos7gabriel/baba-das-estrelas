import requests

# Envio das mensagens
def requisicao_post(mensagem, grupo_id):
    # Prepara a URL e a Autenticação
    url_api = "http://localhost:8080/message/sendText/baba%20das%20estrelas"
    headers = {
        "apikey": "429683C4C977415CAAFCCE10F7D57E11",
        "Content-Type": "application/json"
    }

    # Corpo da requisição com o número do grupo e a mensagem
    corpo_resposta = {
        "number": grupo_id,
        "text": mensagem
    }

    # Requisição POST para enviar a mensagem de volta ao grupo
    try:
        requisição = requests.post(
            url_api, json=corpo_resposta, headers=headers)
        if requisição.status_code == 200 or requisição.status_code == 201:
            print("Resposta enviada com sucesso!")
        else:
            print(
                f"Falha ao enviar a resposta. Status code: {requisição.status_code}, Resposta: {requisição.text}")
    except Exception as e:
        print(f"Erro ao tentar enviar a resposta: {e}")
