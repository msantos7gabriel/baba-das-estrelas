# Importações Extras
import json
from os import environ
from datetime import datetime, timedelta

# Importações Django
from .requisições import (
    requisicao_delete_mensagem,
    requisicao_post,
    requisicao_post_audio,
)
from django.http import JsonResponse
from django.core.cache import cache
import locale
from .eleicao import padrao_eleicao
from django.utils import timezone
# Decoradores
from django.views.decorators.csrf import csrf_exempt
from .decorators import admin_required, cadastro_required

# Modelos
from django.db.models import Q
from .models import Jogador, Baba, ListaDeEspera

# Etapas de comandos de multiplas etapas ficam no cache e expiram sozinhas,
# assim uma etapa esquecida não "sequestra" as próximas mensagens do user
TEMPO_ETAPA = 5 * 60


def get_etapa(id_whatsapp):
    return cache.get(f'etapa:{id_whatsapp}')


def set_etapa(id_whatsapp, comando, **dados):
    # Cada user só tem uma etapa por vez, a nova substitui a anterior
    cache.set(f'etapa:{id_whatsapp}', {'comando': comando, **dados},
              timeout=TEMPO_ETAPA)


def limpar_etapa(id_whatsapp, comando=None):
    # Se o comando for informado, só limpa se a etapa for desse comando
    etapa = get_etapa(id_whatsapp)
    if etapa and (comando is None or etapa['comando'] == comando):
        cache.delete(f'etapa:{id_whatsapp}')


def lista_de_espera_do(baba):
    # Babas criados antes da lista de espera existir não tem uma
    return ListaDeEspera.objects.get_or_create(fk_baba=baba)[0]


try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
except locale.Error:
    print("Locale pt_BR não encontrado. Usando o padrão do sistema.")


# Funcionalidades de ADM


# Funcionalidade para o adm poder soltar a lista
@admin_required
def liberarLista(id_whatsapp, mensagem=None, grupo_id=None):
    baba_aberto = Baba.objects.filter(is_active=True).first()
    if baba_aberto is not None:
        limpar_etapa(id_whatsapp, 'liberarlista')
        texto_resposta = f'Já existe um baba aberto: *{baba_aberto.nome}*\nUse *!fechar* antes de liberar outro.'
        return requisicao_post(texto_resposta, grupo_id)

    # Busca todos os babas cadastrados
    babas = Baba.objects.all().order_by('-data')

    # Se o adm já recebeu a lista, a mensagem é o número do baba escolhido
    etapa = get_etapa(id_whatsapp)
    if mensagem is not None and etapa and etapa['comando'] == 'liberarlista':
        try:
            baba = babas[int(mensagem.strip())-1]
        except (ValueError, IndexError):
            texto_resposta = f"Não existe baba com o número '{mensagem.strip()}'\nResponda com um número da lista de babas ou *!cancelar*."
            return requisicao_post(texto_resposta, grupo_id)

        # Caso seja valido remove a etapa do user
        limpar_etapa(id_whatsapp)
        # Atualizando o baba para ativo
        baba.is_active = True
        baba.save()

        # Mensagem de aviso para informar que o baba foi liberado
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        texto_resposta = f"O Baba '{baba.nome}' foi liberado pelo ADM {jogador.nome}!"
        requisicao_post(texto_resposta, environ.get('CANAL_DE_AVISOS_ID'))
        # Descomente para debugar
        # requisicao_post(texto_resposta, grupo_id)

        # Mensagem de resposta para o grupo informando que o baba foi liberado com sucesso
        texto_resposta = f"Baba '{baba.nome}' liberado com sucesso!"
        return requisicao_post(texto_resposta, grupo_id)

    if babas.count() == 0:
        texto_resposta = f'Não tem nenhum baba cadastrado.\nFale com Gerenciador do Sistema para cadastrar um novo baba'
        return requisicao_post(texto_resposta, grupo_id)

    # Caso tenha babas cadastrados, mostra a lista de babas para o adm escolher qual liberar
    texto_resposta = f'Lista de Babas: \n\n'

    for i in range(len(babas)):
        texto_resposta += f'[{i+1}] - {babas[i]}\n'
    texto_resposta += '\nResponda com o número do baba que deseja liberar:'

    set_etapa(id_whatsapp, 'liberarlista')
    return requisicao_post(texto_resposta, grupo_id)


# Funcionalidade para fechar lista
@admin_required
def fecharLista(id_whatsapp, grupo_id):
    baba_ativo = Baba.objects.filter(is_active=True).first()

    if baba_ativo is None:
        texto_resposta = f'Não tem nenhum baba aberto'
        return requisicao_post(texto_resposta, grupo_id)
    else:
        texto_resposta = f'O Baba {baba_ativo.nome} foi fechado pelo ADM {Jogador.objects.get(id_whatsapp=id_whatsapp).nome}\nObrigado pela presença de todos!'
        requisicao_post(texto_resposta, environ.get('CANAL_DE_AVISOS_ID'))
        # requisicao_post(texto_resposta, grupo_id)

        # Tira o baba para não ativos
        baba_ativo.is_active = False
        baba_ativo.save()

        lista_espera = lista_de_espera_do(baba_ativo)
        jogadores = Jogador.objects.filter(
            Q(baba=baba_ativo) | Q(lista_de_espera=lista_espera))
        for jogador in jogadores:
            if jogador.lista_de_espera is None:
                jogador.jogos += 1
                jogador.baba = None
            else:
                jogador.lista_de_espera = None
            jogador.save()

        texto_resposta = f'Baba {baba_ativo.nome} fechado. A lista e a lista de espera foram zeradas.'
        return requisicao_post(texto_resposta, grupo_id)


# Teste de vida do Bot
def ping(grupo_id):
    texto_resposta = "Tudo funcionando e operacional!"
    return requisicao_post(texto_resposta, grupo_id)


# Informações do bot
def info(grupo_id):
    texto_resposta = (
        "Baba das Estrelas - Bot de gerenciamento da lista do baba.\n\n"
        "Comandos disponíveis:\n"
        "!ping - Verifica se o bot está funcionando.\n"
        "!info, !ajuda ou !menu - Exibe esta lista de comandos.\n"
        "!cadastrar ou !cadastro - Cadastra seu nome.\n"
        "!perfil - Mostra seu perfil e sua posição.\n"
        "!perfil @jogador - Mostra o perfil de outro jogador.\n"
        "!lista - Mostra a lista atual de participantes do baba.\n"
        "!participar ou !entrar - Adiciona você à lista do baba.\n"
        "!adicionar @jogador ou !add @jogador - Adiciona outro jogador cadastrado à lista.\n"
        "!sair - Remove você da lista do baba.\n"
        "!rank - Mostra o ranking de estrelas dos jogadores.\n"
        "!cancelar - Cancela um cadastro ou participação em andamento.\n"
        "\nComandos de ADM:\n"
        "!liberar ou !abrir - Libera a lista de um baba.\n"
        "!fechar - Fecha o baba aberto e zera a lista.\n"
        "!remover @jogador ou !rem @jogador - Tira um jogador da lista.\n"
    )
    return requisicao_post(texto_resposta, grupo_id)


# Cadastro de users
def cadastrar(id_whatsapp, nome=None, grupo_id=None):
    try:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        limpar_etapa(id_whatsapp, 'cadastrar')
        texto_resposta = "Você já está cadastrado."
        return requisicao_post(texto_resposta, grupo_id)
    except Jogador.DoesNotExist:
        # Se o user já recebeu a pergunta, a mensagem é o nome dele
        etapa = get_etapa(id_whatsapp)
        if nome is not None and etapa and etapa['comando'] == 'cadastrar':
            # Verifica se o nome é válido (não vazio e cabe no banco)
            nome = nome.strip()
            if nome == "" or len(nome) > 100:
                texto_resposta = "Nome inválido. Envie só o seu nome (até 100 caracteres) ou *!cancelar*."
                return requisicao_post(texto_resposta, grupo_id)

            limpar_etapa(id_whatsapp)
            jogador = Jogador(nome=nome, id_whatsapp=id_whatsapp)
            jogador.save()
            texto_resposta = f"Cadastro realizado com sucesso!\nUse *!entrar* para entrar na lista quando o baba estiver aberto."
            requisicao_post(texto_resposta, grupo_id)
            return perfil(id_whatsapp, grupo_id=grupo_id)

        set_etapa(id_whatsapp, 'cadastrar')
        texto_resposta = "Qual nome que deseja cadastrar? (Evitar apelidos e caracteres especiais)\nPara desistir, envie *!cancelar*."
        return requisicao_post(texto_resposta, grupo_id)


# Funcionalidades
def estrelas(jogador_estrelas):
    if jogador_estrelas < 6:
        estrelas = f"{int(jogador_estrelas)*'⭐'}"
        # verificar se tem meia estrela
        if (jogador_estrelas - int(jogador_estrelas) > 0):
            estrelas += ' ½'
    else:
        estrelas = f"🌟"

    return estrelas


# informação sobre seu perfil
def texto_perfil(jogador):
    return f"Nome: {jogador.nome}\nNúmero: {jogador.id_whatsapp}\nEstrelas: {estrelas(jogador.estrelas)}\nPosição: {jogador.get_posição()}\nQuantidade de partidas: {jogador.jogos}"


@cadastro_required
def perfil(id_whatsapp,  mensagem=None, grupo_id=None):
    if mensagem == None:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        return requisicao_post(texto_perfil(jogador), grupo_id)

    else:
        mensagem = mensagem.replace('@', '').split()
        try:
            jogador = Jogador.objects.get(id_whatsapp=mensagem[1])
            return requisicao_post(texto_perfil(jogador), grupo_id)

        except Jogador.DoesNotExist:
            texto_resposta = "O Jogador da sua busca não foi encontrado"
            return requisicao_post(texto_resposta, grupo_id)


# Lista do baba
def lista(grupo_id):
    baba_atual = Baba.objects.filter(is_active=True).order_by(
        '-data').first()  # Obtém o último Baba criado

    if not baba_atual:
        texto_resposta = "Nenhum baba aberto no momento."
        return requisicao_post(texto_resposta, grupo_id)

    linha = Jogador.objects.filter(
        baba=baba_atual).filter(jogara='L').order_by("entrou_lista")

    gol = Jogador.objects.filter(
        baba=baba_atual).filter(jogara='G').order_by("entrou_lista")

    if (len(linha) + len(gol)) == 0:
        texto_resposta = "A lista do baba está vazia.\nUse *!entrar* para participar."
    else:
        # Hora e dia podem estar vazios no cadastro do baba
        texto_resposta = f"Lista do {baba_atual.nome}"
        if baba_atual.hora_inicio:
            texto_resposta += f" às {baba_atual.hora_inicio.strftime('%H:%M')}"
        if baba_atual.dia:
            texto_resposta += f" de {baba_atual.dia.strftime('%A').title()}"
        texto_resposta += f":\n\nJogadores ({len(linha)}/{baba_atual.limite_linha}):\n"
        for i in range(len(linha)):
            texto_resposta += f"{i+1}. {linha[i].nome}\n"

        if len(gol) != 0:
            texto_resposta += f'\nGoleiros ({len(gol)}/{baba_atual.limite_gol}):\n'
            for i in range(len(gol)):
                texto_resposta += f"{i+1}. {gol[i].nome}\n"

        lista_espera = lista_de_espera_do(baba_atual)
        jogadores_na_lista = Jogador.objects.filter(
            lista_de_espera=lista_espera).order_by("entrou_lista")

        if jogadores_na_lista.exists():
            texto_resposta += '\nLista de Espera:\n'
            for i in range(len(jogadores_na_lista)):
                texto_resposta += f"{i+1}. {jogadores_na_lista[i].nome} ({Jogador.Posicao(jogadores_na_lista[i].jogara).label})\n"

        texto_resposta += f"{'-' * 30}\nTotal de participantes: {len(linha) + len(gol)}"
        # texto_resposta +=f"\n\nSalve na Agenda:\n https://calendar.google.com/calendar/render?action=TEMPLATE&text={baba_atual.nome.replace(' ','%20')}&dates={baba_atual.data.strftime('%Y%m%d')+baba_atual.hora_inicio.strftime('T%H%M%SZ')}/{baba_atual.data.strftime('%Y%m%d')+baba_atual.hora_fim.strftime('T%H%M%SZ')}&details={baba_atual.descrição.replace(' ','%20')}&location={baba_atual.local.replace(' ','%20')}" # type: ignore
    return requisicao_post(texto_resposta, grupo_id)


# Funções para entrar no baba
def salvar_jogador(jogador, baba, posicao, grupo_id):
    """Função para adicionar a posição ou de goleiro ou linha e um baba a um jogador

    Args:
        jogador (object): Objeto do Banco de dados do Jogador
        grupo_id (str): Id do grupo para retorno da mensagem

    Returns:
        Retorna a função de mostrar a lista para o jogador
    """

    if posicao == 'L':
        limite = baba.limite_linha
    else:
        limite = baba.limite_gol
    ocupadas = Jogador.objects.filter(baba=baba).filter(jogara=posicao).count()

    jogador.entrou_lista = timezone.now()
    jogador.jogara = posicao
    if limite > ocupadas:
        jogador.baba = baba
        jogador.lista_de_espera = None
        jogador.save()
        return lista(grupo_id)

    lista_espera = lista_de_espera_do(baba)
    jogador.lista_de_espera = lista_espera
    jogador.save()

    # Posição do jogador na fila de espera da posição dele
    na_espera = Jogador.objects.filter(
        lista_de_espera=lista_espera).filter(jogara=posicao).count()
    if posicao == 'L':
        texto_resposta = f'A linha está completa ({ocupadas}/{limite}).\n{jogador.nome} entrou na lista de espera da linha ({na_espera}º da fila)'
    else:
        texto_resposta = f'O gol está completo ({ocupadas}/{limite}).\n{jogador.nome} entrou na lista de espera do gol ({na_espera}º da fila)'
    texto_resposta += ' e entra automaticamente quando abrir uma vaga.'
    return requisicao_post(texto_resposta, grupo_id)


def interpretar_posicao(mensagem):
    resposta = mensagem.strip().lower()
    if resposta in ('g', 'gol', 'goleiro'):
        return 'G'
    if resposta in ('l', 'linha'):
        return 'L'
    return None


@cadastro_required
def participar(id_whatsapp, mensagem=None, adicionado=None, grupo_id=None,):
    # Verifica se o jogador é adcionado por outro
    if adicionado == None:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
    else:
        jogador = adicionado

    # Verifica se o jogador já está no baba ou na lista de espera
    if jogador.baba is not None:
        limpar_etapa(id_whatsapp, 'participar')
        texto_resposta = f"{jogador.nome} já está na lista do baba."
        return requisicao_post(texto_resposta, grupo_id)
    if jogador.lista_de_espera is not None:
        limpar_etapa(id_whatsapp, 'participar')
        texto_resposta = f"{jogador.nome} já está na lista de espera do baba."
        return requisicao_post(texto_resposta, grupo_id)

    # Busca o unico baba ativo no momento
    baba = Baba.objects.filter(is_active=True).first()
    if baba == None:
        limpar_etapa(id_whatsapp, 'participar')
        texto_resposta = f'Não há nenhum baba aberto no momento!'
        return requisicao_post(texto_resposta, grupo_id)

    if jogador.posicao != 'A':
        return salvar_jogador(jogador, baba, jogador.posicao, grupo_id)

    # Quem joga no gol e na linha escolhe onde vai jogar.
    # Se o user já recebeu a pergunta, a mensagem é a resposta dele
    etapa = get_etapa(id_whatsapp)
    if mensagem is not None and etapa and etapa['comando'] == 'participar':
        posicao = interpretar_posicao(mensagem)
        if posicao is None:
            texto_resposta = "Não entendi. Responda *G* para gol ou *L* para linha.\nPara desistir, envie *!cancelar*."
            return requisicao_post(texto_resposta, grupo_id)

        limpar_etapa(id_whatsapp)
        return salvar_jogador(jogador, baba, posicao, grupo_id)

    # Guarda só o id do adicionado, o objeto pode mudar até a resposta
    set_etapa(id_whatsapp, 'participar',
              adicionado_id=adicionado.id if adicionado else None)

    if adicionado == None:
        texto_resposta = "Você vai jogar no *Gol* ou na *Linha*? Responda G ou L."
    else:
        texto_resposta = f"{jogador.nome} vai jogar no *Gol* ou na *Linha*? Responda G ou L."
    return requisicao_post(texto_resposta, grupo_id)


@cadastro_required
def sair(id_whatsapp, grupo_id):
    jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
    if jogador.baba is not None:
        jogador.baba = None
        jogador.save()

        texto_resposta = f"O Jogador {jogador.nome} saiu da lista do baba."
        requisicao_post(texto_resposta, grupo_id)

        # Chamando a função de passar o jogador da espera para a lista
        lista_espera_adicao(jogador.jogara, grupo_id)
        return

    elif jogador.lista_de_espera is not None:
        jogador.lista_de_espera = None
        jogador.save()

        texto_resposta = f"O Jogador {jogador.nome} saiu da lista de espera do baba."
        requisicao_post(texto_resposta, grupo_id)
        return

    else:
        texto_resposta = f"{jogador.nome} não está na lista do baba."
        return requisicao_post(texto_resposta, grupo_id)


@cadastro_required
def adicionar(id_whatsapp,  mensagem=None, grupo_id=None):
    if mensagem != None and mensagem != '':
        mensagem_nova = mensagem.replace('@', '').split()
        try:
            jogador_adicionado = Jogador.objects.get(
                id_whatsapp=mensagem_nova[1])
            participar(id_whatsapp=id_whatsapp, grupo_id=grupo_id,
                       adicionado=jogador_adicionado)
            return
        except Jogador.DoesNotExist:
            texto_resposta = "O Jogador da sua busca não foi encontrado"
            return requisicao_post(texto_resposta, grupo_id)

        except Exception as e:
            texto_resposta = f"Erro Inesperado na função adicionar: {e}"
            print(texto_resposta)
            return requisicao_post(texto_resposta, grupo_id)
    else:
        texto_resposta = 'Você não marcou ninguém para adicionar no *BABA*\nUse o comando e marque alguém cadastrado. Ex: *!adicionar @jogador*'
        return requisicao_post(texto_resposta, grupo_id)


@admin_required
def remover(id_whatsapp,  mensagem=None, grupo_id=None):
    if mensagem != None and mensagem != '':
        mensagem_nova = mensagem.replace('@', '').split()
        try:
            Jogador.objects.get(id_whatsapp=mensagem_nova[1])
            sair(id_whatsapp=mensagem_nova[1], grupo_id=grupo_id)
            return
        except Jogador.DoesNotExist:
            texto_resposta = "O Jogador da sua busca não foi encontrado"
            return requisicao_post(texto_resposta, grupo_id)

        except Exception as e:
            print(f"Error: {e}")
            # Garante que tem uma resposta pro erro
            texto_resposta = f"Erro inesperado: {e}"
    else:
        texto_resposta = 'Você não marcou ninguém para remover do *BABA*\nUse o comando e marque o jogador. Ex: *!remover @jogador*'
    return requisicao_post(texto_resposta, grupo_id)


# Cancelar comandos de multiplas etapas
def cancelar(id_whatsapp, grupo_id):
    if get_etapa(id_whatsapp):
        limpar_etapa(id_whatsapp)
        texto_resposta = "Etapa cancelada."
        return requisicao_post(texto_resposta, grupo_id)

    texto_resposta = "Você não está em nenhum processo com mais de uma etapa."
    return requisicao_post(texto_resposta, grupo_id)


def rank(grupo_id):
    jogador = list(Jogador.objects.order_by(
        '-estrelas', '-jogos', 'nome').all())
    texto_resposta = "Ranking:"
    for i in range(Jogador.objects.count()):
        texto_resposta += f'\n{i+1} - {jogador[i].nome} - {estrelas(jogador[i].estrelas)}'
    return requisicao_post(texto_resposta, grupo_id)


# Lista de Espera lógica
def lista_espera_adicao(posicao_liberada, grupo_id):
    baba_atual = Baba.objects.filter(is_active=True).order_by(
        '-data').first()
    if baba_atual is None:
        return

    lista_espera = lista_de_espera_do(baba_atual)
    jogador = Jogador.objects.filter(lista_de_espera=lista_espera).filter(
        jogara=posicao_liberada).order_by("entrou_lista").first()
    if jogador is None:
        return

    texto_resposta = f"{jogador.nome} saiu da lista de espera e entrou no baba!"
    requisicao_post(texto_resposta, grupo_id)
    salvar_jogador(jogador, baba_atual, posicao_liberada, grupo_id)
# Resenha


def entrar_em_biel(nome, grupo_id):
    texto_resposta = f"Banido Permanentemente {nome}"
    return requisicao_post(texto_resposta, grupo_id)


def sadu_ou_don(grupo_id):
    texto_resposta = "É DONNNNNNNNNNNNNNNNNNNNNNNN"
    return requisicao_post(texto_resposta, grupo_id)


def luklima(grupo_id):
    texto_resposta = "Sadu Comeu Luk Lima no banheiro do modelo!"
    return requisicao_post(texto_resposta, grupo_id)


def thiago(grupo_id):
    return requisicao_post('Thiago boquinha de mel puta de Hugo', grupo_id)


def rato(grupo_id):
    return requisicao_post('Qualidades de *ROBERIO ROBSON JUNIOR*:\n- Boquete parafuso\n- Mostrar o pinto no baba\n- Piscar o Cuzin no anal\n- Mama Rindo\n- Recebe Pirocotero no cuzin\n- Boquinha de veludo...', grupo_id)


def hugo(grupo_id):
    return requisicao_post('Thiago dono do cuzinho aveludado(😋🤤) de Hugo', grupo_id)


def passarin(grupo_id):
    # requisicao_post_audio('passarin.mp3', grupo_id)
    # return requisicao_post('AAAAAAAAA LULA MEU PRESIDENTE ☭☭☭', grupo_id)
    return requisicao_post('𝘊𝘰𝘮𝘦𝘯𝘵á𝘳𝘪𝘰 𝘳𝘦𝘮𝘰𝘷𝘪𝘥𝘰 𝘱𝘰𝘳 𝘥𝘦𝘵𝘦𝘳𝘮𝘪𝘯𝘢çã𝘰 𝘥𝘰 𝘔𝘪𝘯𝘪𝘴𝘵𝘳𝘰 𝘈𝘭𝘦𝘹𝘢𝘯𝘥𝘳𝘦 𝘥𝘦 𝘔𝘰𝘳𝘢𝘦𝘴', grupo_id)


def andrey(grupo_id):
    return requisicao_post('*Andrey* melhor chupetinha da Bahia 😋😋🤤🤤', grupo_id)


def lucas(grupo_id):
    return requisicao_post('Rodelinha🍩 de *OURO* 🤤', grupo_id)


def comandos(
    nome,
    mensagem,
    id_whatsapp,
    grupo_id,
    mensagem_id=None,
    from_me=False,
    participante_id=None,
):
    # Mensagens sem texto (ou só com espaços) não tem o que responder
    if not mensagem or not mensagem.strip():
        return

    if cache.get(id_whatsapp):
        print(f"{nome} em cooldown")
        return
    else:
        cache.set(id_whatsapp, True, timeout=1)

    # Comandos validos que o bot pode responder
    commandos_validos = ['!liberar', '!liberar-lista', '!abrir', '!fechar', '!fecha-lista',
                         '!ping', '!info', '!ajuda', '!menu', '!perfil', '!rank', '!lista', '!participar', '!entrar', '!sair', '!adicionar', '!add', '!remover', '!rem',
                         '!cadastrar', '!cadastro', '!cancelar',
                         '!entrar-em-biel', '!sadu-ou-don', '!luklima', '!thiago', '!rato', '!hugo', '!passaro', '!andrey', '!don', '!sadu', '!lucas']

    # Formatação da mensagem para evitar problemas com maiúsculas/minúsculas e espaços
    mensagem_formatada = mensagem.lower().strip()

    if padrao_eleicao.search(mensagem_formatada):
        if mensagem_id:
            return requisicao_delete_mensagem(
                grupo_id, mensagem_id, from_me, participante_id
            )
        print("Não foi possível apagar a mensagem: ID da mensagem ausente.")
        return

    # O comando é sempre a primeira palavra, assim um "!perfil" no meio da
    # conversa não dispara nada. O resto da mensagem é o argumento (ex: @jogador)
    partes = mensagem_formatada.split()
    comando = partes[0]
    argumento = mensagem_formatada if len(partes) > 1 else None

    # Comandos basicos
    if comando in commandos_validos:
        # Debug reasons
        print(
            f"Comando '{mensagem_formatada}' acionado por {nome} no grupo {grupo_id}")

        # Prepara a resposta com base no comando (switch case dps)
        if comando == '!ping':
            ping(grupo_id)
        elif comando == '!info' or comando == '!menu' or comando == '!ajuda':
            info(grupo_id)
        elif comando == '!liberar-lista' or comando == '!liberar' or comando == '!abrir':
            liberarLista(id_whatsapp, grupo_id=grupo_id)
        elif comando == '!fecha-lista' or comando == '!fechar':
            fecharLista(id_whatsapp, grupo_id=grupo_id)
        elif comando == '!perfil':
            perfil(id_whatsapp, mensagem=argumento, grupo_id=grupo_id)
        elif comando == '!lista':
            lista(grupo_id)
        elif comando == '!participar' or comando == '!entrar':
            participar(id_whatsapp, grupo_id=grupo_id)
        elif comando == '!sair':
            sair(id_whatsapp, grupo_id)
        elif comando == '!cadastrar' or comando == '!cadastro':
            cadastrar(id_whatsapp, grupo_id=grupo_id)
        elif comando == '!adicionar' or comando == '!add':
            adicionar(id_whatsapp, mensagem=argumento, grupo_id=grupo_id)
        elif comando == '!remover' or comando == '!rem':
            remover(id_whatsapp, mensagem=argumento, grupo_id=grupo_id)
        elif comando == '!rank':
            rank(grupo_id)
        elif comando == '!cancelar':
            cancelar(id_whatsapp, grupo_id)
        elif comando == '!entrar-em-biel':
            entrar_em_biel(nome, grupo_id)
        elif comando == '!sadu-ou-don' or comando == '!don' or comando == '!sadu':
            sadu_ou_don(grupo_id)
        elif comando == '!luklima':
            luklima(grupo_id)
        elif comando == '!thiago':
            thiago(grupo_id)
        elif comando == '!rato':
            rato(grupo_id)
        elif comando == '!hugo':
            hugo(grupo_id)
        elif comando == '!passaro':
            passarin(grupo_id)
        elif comando == '!andrey':
            andrey(grupo_id)
        elif comando == '!lucas':
            lucas(grupo_id)

    # Comandos que não exitem
    elif comando.startswith('!'):
        return requisicao_post(f'Não existe o comando: *{comando}*! \n*!ajuda* para poder saber os comandos validos', grupo_id)

    else:
        # Mensagem comum: só responde se o user estiver no meio de uma etapa
        etapa = get_etapa(id_whatsapp)
        if etapa is None:
            return

        if etapa['comando'] == 'cadastrar':
            cadastrar(id_whatsapp, nome=mensagem, grupo_id=grupo_id)
        elif etapa['comando'] == 'participar':
            adicionado = None
            if etapa['adicionado_id'] is not None:
                adicionado = Jogador.objects.filter(
                    id=etapa['adicionado_id']).first()
                if adicionado is None:
                    limpar_etapa(id_whatsapp)
                    return
            participar(id_whatsapp, mensagem=mensagem,
                       adicionado=adicionado, grupo_id=grupo_id)
        elif etapa['comando'] == 'liberarlista':
            liberarLista(id_whatsapp, mensagem=mensagem, grupo_id=grupo_id)


# Grupos permitidos
# allowed_groups = ['120363429280772424@g.us',
#                   '120363412694811478@g.us', '120363214522520270@g.us']
allowed_groups = environ.get('ALLOWED_GROUPS', '').split(',')


@csrf_exempt
def webhook_evolution(request):
    if request.method == 'POST':
        try:
            # Pega o JSON enviado pela Evolution
            payload = json.loads(request.body)

            # A Evolution manda qual foi o evento no campo "event"
            evento = payload.get('event')
            dados = payload.get('data', {})
            chaves = dados.get('key', {})

            # Para Verificar o ID do Grupo
            grupo = chaves.get('remoteJid')

            # para verificar se é uma mensagem de conversa ou de mídia
            tipo_mensagem = dados.get('messageType')

            # Para veficar se a mensagem foi enviada a 1 minuto atrás
            date_time = payload.get('date_time').replace(
                'T', ' ').replace('Z', '')
            # Converte a string de data e hora em um objeto datetime
            date_time = datetime.strptime(date_time, '%Y-%m-%d %H:%M:%S.%f')
            time_delta = datetime.now() - date_time

            # Se for uma mensagem nova chegando, se esta dento dos grupos permitidos, e se é uma mensagem de texto e se foi enviada a menos de 1 minuto atrás
            mensagem_textual = tipo_mensagem in (
                'conversation',
                'extendedTextMessage',
            )
            if (
                evento == 'messages.upsert'
                and grupo in allowed_groups
                and mensagem_textual
                and timedelta(minutes=1) > time_delta
            ):
                print("Mensagem atingiu os requisitos")

                # if fromMe:
                #     print("Ignorando minhas prorias mensagens")
                #     return HttpResponse("Ignorando resposta")

                # Nome do User registrado no WhatsApp
                nome = dados.get('pushName', 'Desconhecido')

                # Tenta pegar conversation (texto normal) ou text (texto ao responder alguém)
                mensagem = dados.get('message', {}).get('conversation') or dados.get(
                    'message', {}).get('extendedTextMessage', {}).get('text')

                # em grupos, o remetente pode ser o participante ou a própria conta do bot.
                # Para mensagens de participantes, o valor vem em key.participant; em
                # mensagens do próprio bot, isso pode estar ausente, então usamos um fallback.
                id_whatsapp = str(
                    chaves.get('participant')
                    or chaves.get('remoteJid')
                    or dados.get('sender')
                    or ''
                ).split('@')[0]

                comandos(
                    nome,
                    mensagem,
                    id_whatsapp,
                    grupo,
                    mensagem_id=chaves.get('id') or dados.get('id'),
                    from_me=bool(chaves.get('fromMe', False)),
                    participante_id=chaves.get('participant'),
                )

            else:
                print("Mensagem Não atingiu os requisitos")
                return JsonResponse({'status': 'sucesso'}, status=200)

            return JsonResponse({'status': 'sucesso'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'erro', 'mensagem': 'JSON inválido'}, status=400)

    return JsonResponse({'status': 'metodo_nao_permitido'}, status=405)
