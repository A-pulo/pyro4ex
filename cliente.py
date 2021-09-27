import sys
import threading
import Pyro4
from Pyro4 import util
from datetime import time, timedelta
from random import randrange

sys.excepthook = Pyro4.util.excepthook


@Pyro4.expose
@Pyro4.callback
class ClienteRelogio(object):

    def __init__(self, idf):
        self.__idf = idf
        self.__clock = time(hour=randrange(24), minute=randrange(60))

    def get_clock(self):
        return self.__clock

    def set_clock(self, clock_delta: timedelta):
        self.__clock -= clock_delta
        print(f'cliente.relogio_{self.__idf}: Hora ajustada para {self.__clock} (-{clock_delta})')


def run_client(idf):
    # Inicia o name server para os processos
    nameServer = Pyro4.locateNS(host='localhost', port=9090)

    # Criar processo que vai ficar escutando os requests
    daemon = Pyro4.Daemon()

    # Passar o objeto para ser rodado no daemon. Essa função retorna o endereço do cliente.
    uri = daemon.register(ClienteRelogio(idf))
    print(f"Novo cliente registrado em {uri}")

    # O serviço é vinculado com o metadado "Client" para diferenciar do "Server"
    nameServer.register(f'cliente.relogio_{idf}', uri, metadata={"Client"})
    print("Novo registro no servidor de nomes:")
    print(nameServer.lookup(f'cliente.relogio_{idf}', return_metadata=True))

    # Inicia a escuta de requisições
    threading.Thread(target=daemon.requestLoop).start()
