import json
from .requisições import requisicao_post
from django.http import JsonResponse
from django.core.cache import cache
import locale
# Decoradores
from django.views.decorators.csrf import csrf_exempt
from .decorators import admin_required, cadastro_required
# Modelos
from .models import Jogador, Baba

# Verificador de Etapas de comandos de multiplas etapas
# (ver maneira de fazer com cache, pois o user pode entrar em uma etapa e n terminala)
etapas = []

try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
except locale.Error:
    print("Locale pt_BR não encontrado. Usando o padrão do sistema.")


# Funcionalidades de ADM


# Funcionalidade para o adm poder soltar a lista
@cadastro_required
@admin_required
def liberarLista(id_whatsapp, grupo_id):
    if Baba.objects.filter(is_active=True).count() > 0:
        texto_resposta = f'Já exite um baba aberto'
        return requisicao_post(texto_resposta, grupo_id)
    else:
        texto_resposta = f'Lista de Babas: \n\n'
        babas = Baba.objects.all()
        for i in range(len(babas)):
            texto_resposta += f'[{i}] - {babas[i]}\n'
        texto_resposta += '\n Escolha o baba que deseja liberar:'
        # adicionar etapas
        return requisicao_post(texto_resposta, grupo_id)

# Funcionalidade para fechar lista


@admin_required
def fecharLista(id_whatsapp, grupo_id):
    jogadores = Jogador.objects.all()
    babas = Baba.objects.filter(is_active=True).all()
    if babas == None:
        texto_resposta = f'Não tem nenhum baba aberto'
        return requisicao_post(texto_resposta, grupo_id)
    else:
        # Tira todos os babas para não ativos
        for baba in babas:
            baba.is_active = False
            baba.save()
        for jogador in jogadores:
            jogador.baba = None
            jogador.save()

        texto_resposta = f'Todos os babas ativados os foram fechados, jogadores foram removidos do baba'
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
        "!lista - Mostra a lista atual de participantes do baba.\n"
        "!participar ou !entrar - Adiciona você à lista do baba.\n"
        "!sair - Remove você da lista do baba.\n"
        "!rank - Mostra o ranking de estrelas dos jogadores.\n"
        "!cancelar - Cancela um cadastro ou participação em andamento.\n"
    )
    return requisicao_post(texto_resposta, grupo_id)


# Cadastro de users
def cadastrar(id_whatsapp, nome=None, grupo_id=None):
    try:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        texto_resposta = "Você já está cadastrado."
        return requisicao_post(texto_resposta, grupo_id)
    except Jogador.DoesNotExist:
        for etapa in etapas:
            if etapa[0] == id_whatsapp and etapa[1] == "cadastrar" and etapa[2] == 1:
                # Verifica se o nome é válido (não nulo e não vazio)
                if nome is None or nome.strip() == "":
                    texto_resposta = "Nome inválido. Por favor, tente novamente."
                    return requisicao_post(texto_resposta, grupo_id)

                etapas.remove(etapa)
                jogador = Jogador(nome=nome, id_whatsapp=id_whatsapp)
                jogador.save()
                texto_resposta = f"Cadastro realizado com sucesso!"
                requisicao_post(texto_resposta, grupo_id)
                return perfil(id_whatsapp, grupo_id=grupo_id)

        etapas.append((id_whatsapp, "cadastrar", 1))
        texto_resposta = "Qual nome que deseja cadastrar ?(Evitar apelidos e caracteres especiais)"
        return requisicao_post(texto_resposta, grupo_id)


# Funcionários
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
@cadastro_required
def perfil(id_whatsapp,  mensagem=None, grupo_id=None):
    if mensagem == None:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        texto_resposta = f"Nome: {jogador.nome}\nNúmero: {jogador.id_whatsapp}\nEstrelas: {estrelas(jogador.estrelas)}\nPosicação: {jogador.get_posição()}"
        return requisicao_post(texto_resposta, grupo_id)

    else:
        mensagem = mensagem.replace('@', '').split()
        try:
            jogador = Jogador.objects.get(id_whatsapp=mensagem[1])
            texto_resposta = f"Nome: {jogador.nome}\nNúmero: {jogador.id_whatsapp}\nEstrelas: {estrelas(jogador.estrelas)}\nPosicação: {jogador.get_posição()}"
            return requisicao_post(texto_resposta, grupo_id)

        except Jogador.DoesNotExist:
            texto_resposta = "O Jogador da sua busca não foi encontrado"
            return requisicao_post(texto_resposta, grupo_id)


# Lista do baba
def lista(grupo_id):
    baba_atual = Baba.objects.order_by(
        '-data').filter(is_active=True).first()  # Obtém o último Baba criado
    print(baba_atual)

    if not baba_atual:
        texto_resposta = "Nenhum baba criado."
        return requisicao_post(texto_resposta, grupo_id)

    linha = Jogador.objects.filter(
        baba=baba_atual).filter(jogara='L')

    gol = Jogador.objects.filter(
        baba=baba_atual).filter(jogara='G')

    if (len(linha) + len(gol)) == 0:
        texto_resposta = "A lista do baba está vazia."
    else:
        texto_resposta = (
            f"Lista do {baba_atual.nome} ás {baba_atual.hora_inicio.strftime('%H:%M')} de {baba_atual.dia.strftime('%A').title()}:\n")  # type: ignore
        texto_resposta += f"\nJogadores:\n"
        for i in range(len(linha)):
            texto_resposta += f"{i+1}. {linha[i].nome}\n"

        if len(gol) != 0:
            texto_resposta += '\nLista de Goleiros:\n'
            for i in range(len(gol)):
                texto_resposta += f"{i+1}. {gol[i].nome}\n"

        texto_resposta += f"{'-' * 75}\nTotal de participantes: {len(linha) + len(gol)}"
        # texto_resposta +=f"\n\nSalve na Agenda:\n https://calendar.google.com/calendar/render?action=TEMPLATE&text={baba_atual.nome.replace(' ','%20')}&dates={baba_atual.data.strftime('%Y%m%d')+baba_atual.hora_inicio.strftime('T%H%M%SZ')}/{baba_atual.data.strftime('%Y%m%d')+baba_atual.hora_fim.strftime('T%H%M%SZ')}&details={baba_atual.descrição.replace(' ','%20')}&location={baba_atual.local.replace(' ','%20')}" # type: ignore
    return requisicao_post(texto_resposta, grupo_id)


def salvar_jogador(jogador, baba, posicao, grupo_id):
    """Função para adicionar a posição ou de goleiro ou linha e um baba a um jogador

    Args:
        jogador (object): Objeto do Banco de dados do Jogador
        grupo_id (str): Id do grupo para retorno da mensagem

    Returns:
        Retorna a função de mostrar a lista para o jogador
    """

    qtd_jogadores_linha = Jogador.objects.filter(
        baba=baba).filter(jogara='L').count()

    qtd_jogadores_gol = Jogador.objects.filter(
        baba=baba).filter(jogara='G').count()

    if posicao == 'L':
        if baba.limite_linha > qtd_jogadores_linha:
            jogador.baba = baba
            jogador.jogara = 'L'
            jogador.save()
        else:
            texto_resposta = 'O Baba ja atingiu seu limite de pessoas na linha'
            return requisicao_post(texto_resposta, grupo_id)
    else:
        if baba.limite_gol > qtd_jogadores_gol:
            jogador.baba = baba
            jogador.jogara = 'G'
            jogador.save()
        else:
            texto_resposta = 'O Baba ja atingiu seu limite de pessoas no gol'
            return requisicao_post(texto_resposta, grupo_id)
    return lista(grupo_id)


@cadastro_required
def participar(id_whatsapp, mensagem=None, grupo_id=None):
    # Implementar lógica para escolher se quer ser goleirou ou linha
    try:
        jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
        # Verifica se o jogador está associado a um Baba existente
        if jogador.baba is not None:
            texto_resposta = f"Você já está cadastrado e associado ao baba '{jogador.baba.nome}'."
            return requisicao_post(texto_resposta, grupo_id)
        else:
            raise Baba.DoesNotExist  # Força a criação de um novo Baba para o jogador

    except Baba.DoesNotExist:
        # Se o jogador não estiver associado a um Baba verifica sua posição e adiciona ele no baba

        # Busca o unico baba ativo no momento
        baba = Baba.objects.filter(is_active=True).first()
        if baba == None:
            texto_resposta = f'Não há nenhum baba aberto!'
            return requisicao_post(texto_resposta, grupo_id)

        if jogador.posicao == 'A':
            # Verifica se ele esta em alguma etapa
            for etapa in etapas:
                if etapa[0] == id_whatsapp and etapa[1] == "participar" and etapa[2] == 1:
                    # Verifica se a mensa é válida (não nulo e não vazio) e se ele é sim ou não
                    if mensagem is None or mensagem.strip() == "" or mensagem.lower() not in ['g', 'l']:
                        texto_resposta = "Mensagem inválida. Por favor, tente novamente."
                        return requisicao_post(texto_resposta, grupo_id)
                    else:
                        if mensagem.lower() == 'g':
                            etapas.remove(etapa)
                            return salvar_jogador(jogador, baba, 'G', grupo_id,)
                        else:
                            etapas.remove(etapa)
                            return salvar_jogador(jogador, baba, 'L', grupo_id)

            # Caso o user não esteja em uma etapa
            etapas.append((id_whatsapp, "participar", 1))
            texto_resposta = "Deseja Jogar no Gol ou na linha ? (G/L)"
            return requisicao_post(texto_resposta, grupo_id)

        elif jogador.posicao == 'G':
            salvar_jogador(jogador, baba, jogador.posicao,  grupo_id,)
        else:
            salvar_jogador(jogador, baba, jogador.posicao,  grupo_id,)


@cadastro_required
def sair(id_whatsapp, grupo_id):
    jogador = Jogador.objects.get(id_whatsapp=id_whatsapp)
    if jogador.baba is not None:
        jogador.baba = None
        jogador.save()
        texto_resposta = f"Você saiu da lista do baba."
        return requisicao_post(texto_resposta, grupo_id)
    else:
        texto_resposta = f"Você não está associado a nenhum baba."
        return requisicao_post(texto_resposta, grupo_id)


# Cancelar comandos de multiplas etapas
def cancelar(id_whatsapp, grupo_id):
    for etapa in etapas:
        if etapa[0] == id_whatsapp:
            etapas.remove(etapa)
            texto_resposta = "Etapa cancelada."
            return requisicao_post(texto_resposta, grupo_id)

    texto_resposta = "Você não está em nenhum processo com mais de uma etapa."
    return requisicao_post(texto_resposta, grupo_id)


def rank(grupo_id):
    jogador = list(Jogador.objects.order_by('-estrelas', 'nome').all())
    texto_resposta = "Ranking:"
    for i in range(Jogador.objects.count()):
        texto_resposta += f'\n{i+1} - {jogador[i].nome} - {estrelas(jogador[i].estrelas)}'
    return requisicao_post(texto_resposta, grupo_id)


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
    return requisicao_post('AAAAAAAAA LULA MEU PRESIDENTE ☭☭☭', grupo_id)


def andrey(grupo_id):
    return requisicao_post('*Andrey* melhor chupetinha da Bahia 😋😋🤤🤤', grupo_id)


def comandos(nome, mensagem, id_whatsapp, grupo_id):
    if cache.get(id_whatsapp):
        print(f"{nome} em cooldown")
        return
    else:
        cache.set(id_whatsapp, True, timeout=1)

    # Comandos validos que o bot pode responder
    commandos_validos = ['!liberar', '!liberar-lista', '!fechar', '!fecha-lista',
                         '!ping', '!info', '!ajuda', '!menu', '!perfil', '!rank', '!lista', '!participar', '!entrar', '!sair',
                         '!cadastrar', '!cadastro', '!cancelar',
                         '!entrar-em-biel', '!sadu-ou-don', '!luklima', '!thiago', '!rato', '!hugo', '!passaro', '!andrey', '!don', '!sadu']

    # Formatação da mensagem para evitar problemas com maiúsculas/minúsculas e espaços
    mensagem_formatada = mensagem.lower().strip()

    # Comandos basicos
    if mensagem_formatada in commandos_validos:
        # Debug reasons
        print(
            f"Comando '{mensagem_formatada}' acionado por {nome} no grupo {grupo_id}")

        # Prepara a resposta com base no comando (switch case dps)
        if mensagem_formatada == '!ping':
            ping(grupo_id)
        elif mensagem_formatada == '!info' or mensagem_formatada == '!menu' or mensagem_formatada == '!ajuda':
            info(grupo_id)
        elif mensagem_formatada == '!liberar-lista' or mensagem_formatada == '!liberar':
            liberarLista(id_whatsapp, grupo_id)
        elif mensagem_formatada == '!fecha-lista' or mensagem_formatada == '!fechar':
            fecharLista(id_whatsapp, grupo_id)
        elif mensagem_formatada == '!perfil':
            perfil(id_whatsapp, grupo_id=grupo_id)
        elif mensagem_formatada == '!lista':
            lista(grupo_id)
        elif mensagem_formatada == '!participar' or mensagem_formatada == '!entrar':
            participar(id_whatsapp, grupo_id=grupo_id)
        elif mensagem_formatada == '!sair':
            sair(id_whatsapp, grupo_id)
        elif mensagem_formatada == '!cadastrar' or mensagem_formatada == '!cadastro':
            cadastrar(id_whatsapp, grupo_id=grupo_id)
        elif mensagem_formatada == '!rank':
            rank(grupo_id)
        elif mensagem_formatada == '!cancelar':
            cancelar(id_whatsapp, grupo_id)
        elif mensagem_formatada == '!entrar-em-biel':
            entrar_em_biel(nome, grupo_id)
        elif mensagem_formatada == '!sadu-ou-don' or mensagem_formatada == '!don' or mensagem_formatada == '!sadu':
            sadu_ou_don(grupo_id)
        elif mensagem_formatada == '!luklima':
            luklima(grupo_id)
        elif mensagem_formatada == '!thiago':
            thiago(grupo_id)
        elif mensagem_formatada == '!rato':
            rato(grupo_id)
        elif mensagem_formatada == '!hugo':
            hugo(grupo_id)
        elif mensagem_formatada == '!passaro':
            passarin(grupo_id)
        elif mensagem_formatada == '!andrey':
            andrey(grupo_id)
    else:
        # Verificar se o user esta em uma etapa de cadastro
        for etapa in etapas:
            if etapa[0] == id_whatsapp and etapa[1] == "cadastrar":
                cadastrar(id_whatsapp, nome=mensagem, grupo_id=grupo_id)
            elif etapa[0] == id_whatsapp and etapa[1] == "participar":
                participar(id_whatsapp, mensagem, grupo_id)

        # Commandos compostos
        if '!perfil' in mensagem_formatada:
            perfil(id_whatsapp, grupo_id=grupo_id,
                   mensagem=mensagem_formatada)
            return

        # Comandos que não exitem
        if '!' in mensagem_formatada[0]:
            return requisicao_post(f'Não existe o comando: *{mensagem_formatada}*! \n*!ajuda* para poder saber os comandos validos', grupo_id)


# Grupos permitidos
allowed_groups = ['120363429280772424@g.us',
                  '120363412694811478@g.us', '120363214522520270@g.us']


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

            # verifica se é uma mensagem de conversa ou de mídia
            tipo_mensagem = dados.get('messageType')

            # Se for uma mensagem nova chegando...
            if evento == 'messages.upsert' and grupo in allowed_groups and tipo_mensagem == 'conversation':
                print("Mensagem atingiu os requisitos")

                # if fromMe:
                #     print("Ignorando minhas prorias mensagens")
                #     return HttpResponse("Ignorando resposta")

                # Nome do User registrado no WhatsApp
                nome = dados.get('pushName', 'Desconhecido')

                # Tenta pegar conversation (texto normal) ou text (texto ao responder alguém)
                mensagem = dados.get('message', {}).get('conversation') or dados.get(
                    'message', {}).get('extendedTextMessage', {}).get('text')

                # id whatsapp
                id_whatsapp = str(chaves.get('participant')).split('@')[0]

                comandos(nome, mensagem,
                         id_whatsapp, grupo)

            else:
                print("Mensagem Não atingiu os requisitos")
                return JsonResponse({'status': 'sucesso'}, status=200)

            return JsonResponse({'status': 'sucesso'}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({'status': 'erro', 'mensagem': 'JSON inválido'}, status=400)

    return JsonResponse({'status': 'metodo_nao_permitido'}, status=405)
