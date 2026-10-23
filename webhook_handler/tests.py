import json
import time
from datetime import datetime
from unittest import mock

from django.core.cache import cache
from django.test import TestCase

from . import views
from .models import Baba, Jogador, ListaDeEspera

GRUPO = '123456@g.us'


class BotTestCase(TestCase):
    """Base dos testes: captura as mensagens que o bot enviaria pro WhatsApp"""

    def setUp(self):
        cache.clear()
        self.enviadas = []

        def capturar(texto, grupo_id):
            self.enviadas.append(texto)

        for alvo in ('webhook_handler.views.requisicao_post',
                     'webhook_handler.decorators.requisicao_post'):
            patcher = mock.patch(alvo, side_effect=capturar)
            patcher.start()
            self.addCleanup(patcher.stop)

    def enviar(self, id_whatsapp, mensagem, nome='Teste'):
        """Simula uma mensagem no grupo e devolve as respostas do bot"""
        self.enviadas.clear()
        # Remove o cooldown de 1s entre mensagens do mesmo user
        cache.delete(id_whatsapp)
        views.comandos(nome, mensagem, id_whatsapp, GRUPO)
        return list(self.enviadas)


class CadastroTests(BotTestCase):
    def test_cadastrar_pede_nome_e_cadastra(self):
        self.assertIn('Qual nome', self.enviar('100', '!cadastrar')[0])
        respostas = self.enviar('100', 'João Silva')

        self.assertEqual(Jogador.objects.get(id_whatsapp='100').nome, 'João Silva')
        self.assertIn('!entrar', respostas[0])

    def test_comando_durante_cadastro_nao_vira_nome(self):
        self.enviar('100', '!cadastro')
        self.enviar('100', '!xyz')

        self.assertFalse(Jogador.objects.filter(id_whatsapp='100').exists())

    def test_cancelar_encerra_etapa(self):
        self.enviar('100', '!cadastro')

        self.assertEqual(self.enviar('100', '!cancelar'), ['Etapa cancelada.'])
        self.assertEqual(self.enviar('100', 'João'), [])
        self.assertFalse(Jogador.objects.filter(id_whatsapp='100').exists())

    def test_etapa_esquecida_expira(self):
        self.enviar('100', '!cadastro')

        depois = time.time() + views.TEMPO_ETAPA + 1
        with mock.patch('time.time', return_value=depois):
            respostas = self.enviar('100', 'bora jogar hoje')

        self.assertEqual(respostas, [])
        self.assertFalse(Jogador.objects.filter(id_whatsapp='100').exists())


class RoteamentoTests(BotTestCase):
    def test_mensagem_sem_texto_e_ignorada(self):
        self.assertEqual(self.enviar('100', None), [])
        self.assertEqual(self.enviar('100', '   '), [])

    def test_comando_no_meio_da_conversa_nao_dispara(self):
        self.assertEqual(self.enviar('100', 'alguém sabe usar o !perfil?'), [])
        self.assertEqual(self.enviar('100', 'manda o !add pra ele'), [])

    def test_comando_desconhecido(self):
        self.assertIn('Não existe o comando', self.enviar('100', '!perfilx')[0])

    def test_ajuda_mostra_todos_os_comandos(self):
        resposta = self.enviar('100', '!ajuda')[0]

        for comando in ('!cadastrar', '!adicionar', '!remover', '!liberar', '!fechar'):
            self.assertIn(comando, resposta)

    def test_texto_da_ajuda_nao_dispara_comandos(self):
        # O bot também recebe as próprias mensagens pelo webhook
        texto_ajuda = self.enviar('100', '!ajuda')[0]

        self.assertEqual(self.enviar('999', texto_ajuda), [])

    def test_perfil_de_outro_jogador(self):
        Jogador.objects.create(nome='Ana', id_whatsapp='200')
        Jogador.objects.create(nome='Bia', id_whatsapp='201')

        self.assertIn('Nome: Bia', self.enviar('200', '!perfil @201')[0])


class ListaTests(BotTestCase):
    def setUp(self):
        super().setUp()
        self.baba = Baba.objects.create(limite_linha=1, limite_gol=1, is_active=True)
        self.ana = Jogador.objects.create(nome='Ana', id_whatsapp='200')
        self.bia = Jogador.objects.create(nome='Bia', id_whatsapp='201')
        self.caio = Jogador.objects.create(nome='Caio', id_whatsapp='202', posicao='A')

    def test_lista_sem_baba_aberto(self):
        self.baba.is_active = False
        self.baba.save()

        self.assertEqual(self.enviar('200', '!lista'), ['Nenhum baba aberto no momento.'])

    def test_lista_mostra_vagas_ocupadas(self):
        resposta = self.enviar('200', '!entrar')[0]

        self.assertIn('Jogadores (1/1)', resposta)

    def test_entrar_duas_vezes_avisa_onde_esta(self):
        self.enviar('200', '!entrar')

        self.assertEqual(self.enviar('200', '!entrar'), ['Ana já está na lista do baba.'])

    def test_lista_cheia_vai_para_espera_e_sobe_quando_abre_vaga(self):
        self.enviar('200', '!entrar')

        self.assertIn('Bia entrou na lista de espera', self.enviar('201', '!entrar')[0])
        self.assertIn('Bia (Linha)', self.enviar('200', '!lista')[0])

        respostas = self.enviar('200', '!sair')
        self.assertIn('Bia saiu da lista de espera e entrou no baba!', respostas)
        self.bia.refresh_from_db()
        self.assertEqual(self.bia.baba, self.baba)
        self.assertIsNone(self.bia.lista_de_espera)

    def test_jogador_de_duas_posicoes_escolhe_onde_jogar(self):
        self.assertIn('*Gol* ou na *Linha*', self.enviar('202', '!entrar')[0])
        self.assertIn('!cancelar', self.enviar('202', 'talvez')[0])
        self.enviar('202', 'Goleiro')

        self.caio.refresh_from_db()
        self.assertEqual((self.caio.baba, self.caio.jogara), (self.baba, 'G'))

    def test_adicionar_jogador_de_duas_posicoes_pergunta_pelo_nome(self):
        self.assertIn('Caio', self.enviar('200', '!add @202')[0])
        self.enviar('200', 'linha')

        self.caio.refresh_from_db()
        self.assertEqual((self.caio.baba, self.caio.jogara), (self.baba, 'L'))

    def test_remover_exige_adm(self):
        self.enviar('201', '!entrar')

        self.assertIn('privilégios', self.enviar('200', '!rem @201')[0])

        self.ana.is_admin = True
        self.ana.save()
        self.enviar('200', '!rem @201')
        self.bia.refresh_from_db()
        self.assertIsNone(self.bia.baba)


@mock.patch.dict('os.environ', {'CANAL_DE_AVISOS_ID': GRUPO})
class AdmTests(BotTestCase):
    def setUp(self):
        super().setUp()
        self.adm = Jogador.objects.create(nome='Adm', id_whatsapp='300', is_admin=True)
        self.baba = Baba.objects.create(nome='Baba de Sexta')

    def test_liberar_e_fechar_lista(self):
        self.assertIn('[1] - Baba de Sexta', self.enviar('300', '!liberar')[0])
        self.assertIn('Não existe baba', self.enviar('300', '9')[0])
        self.enviar('300', '1')
        self.baba.refresh_from_db()
        self.assertTrue(self.baba.is_active)

        self.enviar('300', '!entrar')
        self.enviar('300', '!fechar')
        self.baba.refresh_from_db()
        self.adm.refresh_from_db()
        self.assertFalse(self.baba.is_active)
        self.assertEqual((self.adm.baba, self.adm.jogos), (None, 1))

    def test_liberar_com_baba_aberto_avisa_qual(self):
        self.baba.is_active = True
        self.baba.save()

        self.assertIn('Baba de Sexta', self.enviar('300', '!liberar')[0])

    def test_baba_antigo_sem_lista_de_espera(self):
        # Babas criados antes da lista de espera existir não têm ListaDeEspera
        ListaDeEspera.objects.filter(fk_baba=self.baba).delete()
        Baba.objects.filter(pk=self.baba.pk).update(is_active=True, limite_linha=0)

        self.assertIn('lista de espera', self.enviar('300', '!entrar')[0])
        self.enviar('300', '!fechar')
        self.adm.refresh_from_db()
        self.assertIsNone(self.adm.lista_de_espera)


class WebhookTests(BotTestCase):
    def payload(self, mensagem):
        return {
            'event': 'messages.upsert',
            'date_time': datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'data': {
                'key': {'remoteJid': GRUPO, 'participant': '100@s.whatsapp.net', 'id': 'abc'},
                'pushName': 'Teste',
                'messageType': 'extendedTextMessage',
                'message': mensagem,
            },
        }

    def post(self, payload):
        with mock.patch.object(views, 'allowed_groups', [GRUPO]):
            return self.client.post('/webhook/evolution/', data=json.dumps(payload),
                                    content_type='application/json')

    def test_mensagem_sem_texto_nao_quebra(self):
        resposta = self.post(self.payload({'extendedTextMessage': {}}))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.enviadas, [])

    def test_comando_pelo_webhook(self):
        resposta = self.post(self.payload({'conversation': '!ping'}))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(self.enviadas, ['Tudo funcionando e operacional!'])
