import re

filtro_eleitoral = [
    # Termos centrais e variações (com e sem acento)
    "eleição", "eleicao", "eleições", "eleicoes", "eleições 2026", "eleicoes 2026",
    "pleito", "escrutínio", "escrutinio", "sufrágio", "sufragio", "democracia", "processo eleitoral",

    # Candidatos e políticos gerais
    "candidato", "candidatos", "candidata", "candidatas", "candidatura", "candidaturas",
    "político", "politico", "políticos", "politicos", "política", "politica",
    "políticas", "politicas", "chapa", "chapas", "vice", "suplente",

    # Cargos em disputa
    "presidente", "presidentes", "governador", "governadores", "governadora", "governadoras",
    "senador", "senadores", "senadora", "senadoras", "deputado", "deputados", "deputado federal", "deputado estadual",
    "deputada", "deputadas", "prefeito", "prefeitos", "prefeita", "prefeitas",
    "vereador", "vereadores", "vereadora", "vereadoras",

    # Votação e eleitores
    "voto", "votos", "votação", "votacao", "votar", "votou", "votaram",
    "eleitor", "eleitores", "eleitora", "eleitoras", "eleitorado",
    "urna", "urnas", "urna eletrônica", "urna eletronica",
    "abstenção", "abstencao", "voto nulo", "voto branco", "voto válido", "voto valido",
    "apuração", "apuracao", "contagem de votos", "zona eleitoral", "seção eleitoral",
    "secao eleitoral", "título de eleitor", "titulo de eleitor", "mesário", "mesario",
    "mesária", "mesaria", "biometria",

    # Campanha e marketing político
    "campanha", "campanhas", "comício", "comicio", "comícios", "comicios",
    "carreata", "carreatas", "passeata", "passeatas", "palanque", "palanques",
    "santinho", "santinhos", "propaganda eleitoral", "horário eleitoral", "horario eleitoral",
    "debate", "debates", "slogan", "marqueteiro", "boca de urna",

    # Sistema e partidos (Nomes das siglas)
    "partido", "partidos", "partidário", "partidario", "sigla", "siglas",
    "coligação", "coligacao", "coligações", "coligacoes", "federação partidária", "federacao partidaria",
    "tse", "tre", "stf", "justiça eleitoral", "justica eleitoral", "legenda", "quociente eleitoral",
    "filiado", "filiação", "filiacao",
    "pt", "pl", "psol", "mdb", "psd", "pp", "republicanos", "uniao brasil", "pdt", "psb", "psdb", "novo",

    # Pós-eleição
    "reeleição", "reeleicao", "mandato", "mandatos", "posse",
    "diplomação", "diplomacao", "primeiro turno", "segundo turno",

    # Nomes nacionais 2026, presidenciáveis, apelidos e variações
    "lula", "luiz inácio", "luiz inacio", "petista", "lulista", "faz o l", "molusco", "mula", "nove dedos", "janja",
    "bolsonaro", "jair", "flavio", "eduardo bolsonaro", "carlos bolsonaro", "michelle bolsonaro", "bolsonarista", "mito", "bozo", "bonoro", "biroliro", "bolso", "vorcaro", "capitão", "capitao",
    "tarcísio", "tarcisio", "tarcisio de freitas", "zema", "romeu zema", "caiado", "ronaldo caiado", "ratinho júnior", "ratinho junior", "eduardo leite", "helder barbalho",
    "ciro", "ciro gomes", "cirista", "marina silva", "simone tebet", "tebet", "haddad", "fernando haddad", "flavio dino", "silvio almeida",
    "boulos", "guilherme boulos", "marçal", "pablo marçal", "pablo marcal", "faz o m",
    "datena", "tabata", "tabata amaral", "nunes", "ricardo nunes",
    "moraes", "xandão", "xandao", "alexandre de moraes", "arthur lira", "rodrigo pacheco",
    "renan", "renan santos", "gleisi", "valdemar",

    # Nomes fortes da Bahia e política local (Foco Salvador / Sertão / Guanambi)
    "jerônimo", "jeronimo", "jeronimo rodrigues", "rui costa", "jaques wagner", "acm", "acm neto", "bruno reis", "geraldo júnior", "geraldo junior", "otto alencar", "angelo coronel", "joão roma", "joao roma", "elmar nascimento", "antonio brito",
    "nilo coelho", "charles fernandes", "jairo magalhães", "jairo magalhaes", "naldo azevedo", "hugo costa", "felipe duarte", "rodrigo boa sorte", "vandilson medeiros",

    # Termos de polarização e gírias de internet
    "esquerdista", "direitista", "esquerdopata", "fascista", "comunista", "extrema-direita", "extrema-esquerda", "centrão", "centrao",
    "gado", "mortadela", "coxinha", "isentão", "isentao", "patriota", "comunismo", "fascismo", "ditadura", "golpe", "anistia",

    # Numeros dos principais partidos (Cuidado: números curtos podem bloquear coisas do futebol)
    # "13", "14", "22", "44", "15", "11", "55", "10", "30", "12", "50", "45", "40",

    # Anarcocapitalismo, Libertarianismo e Escola Austríaca
    "luli", "Lulo", "p3tista", "21+1", "flávio", "petistas", "Lulala", "donald trump", "donald", "trump", "pretistas", "chupetinha", "anarcocapitalismo", "anarco", "ancapistão",

    # Anarcocapitalismo, Libertarianismo e Escola Austríaca
    "anarcocapitalismo", "anarco capitalismo", "ancap", "ancaps", "libertário", "libertario", "libertarianismo",
    "imposto é roubo", "imposto e roubo", "pna", "princípio de não agressão", "principio de nao agressao",
    "escola austríaca", "escola austriaca", "estatista", "privatizar tudo", "don't tread on me", "cobra amarela",

    # Autores clássicos do movimento
    "rothbard", "murray rothbard", "mises", "von mises", "hans-hermann hoppe", "hoppe", "hayek",

    # Figuras e canais brasileiros ligados ao movimento (Kogos, Trezoitão, Ideias Radicais, etc.)
    "paulo kogos", "kogos", "renato trezoitão", "trezoitao", "trezoitão", "ideias radicais", "rafael hide", "rafael lima",

    # Conflitos Internacionais e Geopolítica
    "israel", "isr4el", "israel livre", "isr4el livre", "estado de israel",
    "povo judeu", "povo judeu livre", "sionista", "sionismo",
    "palestina", "palestina livre", "estado da palestina", "gaza", "faixa de gaza", "hamas", "luli", "4 dedo", "4 dedos", "b0Lsonar0", "f l a v i o", "esquerda", "direita"
]

padrao_eleicao = re.compile(
    r"\b(?:" + "|".join(re.escape(termo)
                        for termo in filtro_eleitoral) + r")\b",
    re.IGNORECASE,
)
