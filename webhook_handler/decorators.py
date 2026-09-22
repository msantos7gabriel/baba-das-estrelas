from functools import wraps
from .requisições import requisicao_post
from .models import Jogador


def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extrai os dados de forma segura (verifica no kwargs primeiro, se não, pega do args)
        id_whatsapp = kwargs.get('id_whatsapp') if 'id_whatsapp' in kwargs else (
            args[0] if args else None)
        grupo_id = kwargs.get('grupo_id') if 'grupo_id' in kwargs else (
            args[-1] if args else None)

        try:
            jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
            if jogador.is_admin:
                return func(*args, **kwargs)
            else:
                return requisicao_post(
                    'Você não possui os privilégios necessários para finalizar essa requisição', grupo_id)
        except Jogador.DoesNotExist:
            return requisicao_post('Você não está cadastrado.', grupo_id)

    return wrapper


def cadastro_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extrai os dados de forma segura
        id_whatsapp = kwargs.get('id_whatsapp') if 'id_whatsapp' in kwargs else (
            args[0] if args else None)
        grupo_id = kwargs.get('grupo_id') if 'grupo_id' in kwargs else (
            args[-1] if args else None)

        try:
            Jogador.objects.get(id_whatsapp=id_whatsapp)
        except Jogador.DoesNotExist:
            return requisicao_post(
                'Você não está cadastrado. Use o comando !cadastrar para se cadastrar', grupo_id)
        except Exception as e:
            print(f'error no decorador cadastro_required: {e}')
            return
        return func(*args, **kwargs)
    return wrapper
