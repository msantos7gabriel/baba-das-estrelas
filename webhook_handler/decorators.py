from functools import wraps
from .requisições import requisicao_post
from .models import Jogador

# Args[0] = id do zap
# Args[-1] = id do grupo

def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        jogador = Jogador.objects.get(id_whatsapp=args[0])
        if jogador.is_admin:
            return func(*args, **kwargs)
        else:
            requisicao_post(
                'Você não possui os privilégios necessários para finzalizar essa requisição', args[-1])
    return wrapper


def cadastro_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):

        destino = kwargs.get('grupo_id') or args[-1]
        try:
            Jogador.objects.get(id_whatsapp=args[0])
            return func(*args, **kwargs)
        except Jogador.DoesNotExist:
            return requisicao_post(
                'Você não está cadastrado. Use o comando !cadastrar para se cadastrar', destino)
        except Exception as e:
            print(f'error: {e}')
            return
    return wrapper
