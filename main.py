import sys
import threading
import cliente
import Pyro4
from Pyro4 import naming, util
from datetime import datetime, time, timedelta
from random import randrange


# No contexto do Pyro4, tanto os clientes quanto o servidor para a implementação do algoritimo
# de Berkeley serão objetos remotos


@Pyro4.expose
class ServidorRelogio(object):

    def __init__(self):
        self.__client_seq = 0
        self.__clock = time(hour=randrange(24), minute=randrange(60), second=randrange(60))

    def new_client_seq(self):
        self.__client_seq += 1
        return self.__client_seq

    def get_clock(self):
        return self.__clock

    # Método para atualizar o relógio a partir de um valor de ajuste recebido
    def set_clock(self, flag, clock_delta):
        clock_delta = timedelta(seconds=clock_delta)
        hora = self.__clock
        hora = datetime.combine(datetime.today(), hora)
        if flag == '-':
            hora -= clock_delta
        elif flag == '+':
            hora += clock_delta
        hora_antiga = self.__clock
        self.__clock = hora.time()
        print(f'servidor.relogio: Hora ajustada de {hora_antiga} para {self.__clock} ({flag}{clock_delta})')

    # Algorimimo de ajuste dos relógios
    def berkeley(self, li_clientes: dict):
        hora = datetime.strptime(str(self.get_clock()), "%H:%M:%S").time()
        relogios = {naming.resolve("PYRONAME:servidor.relogio"): hora}
        # Cria um dicionario de cliente: relogio
        for pyroname in li_clientes:
            clienteUri = li_clientes[pyroname]
            with Pyro4.Proxy(clienteUri) as proxy_cliente:
                hora = datetime.strptime(str(proxy_cliente.get_clock()), "%H:%M:%S").time()
                relogios[clienteUri] = hora

        # Calcula a média dos horarios coletados
        delta = timedelta()
        for cliente_uri in relogios:
            hora_delta = timedelta(hours=relogios[cliente_uri].hour,
                                   minutes=relogios[cliente_uri].minute,
                                   seconds=relogios[cliente_uri].second)
            relogios[cliente_uri] = hora_delta
            delta += hora_delta
        delta /= len(relogios)

        # Aplica a diferença da média e envia aos clientes para atualização
        for cliente_uri in relogios:
            hora_cliente = relogios[cliente_uri]
            if hora_cliente > delta:
                relogios[cliente_uri] -= delta
                flag = '-'
            else:
                relogios[cliente_uri] = delta - relogios[cliente_uri]
                flag = '+'
            with Pyro4.Proxy(cliente_uri) as proxy_cliente:
                proxy_cliente.set_clock(flag, relogios[cliente_uri])


if __name__ == '__main__':

    # Inicia o name server para os processos
    threading.Thread(target=Pyro4.naming.startNSloop).start()
    nameServer = Pyro4.locateNS(host='localhost', port=9090)

    # Criar processo que vai ficar escutando os requests
    daemon = Pyro4.Daemon()

    # Passar o objeto do servidor para ser rodado no daemon. Essa função retorna o endereço do servidor.
    uri = daemon.register(ServidorRelogio())
    print(f"Servidor registrado em {uri}")

    # Vincula o endereço do servidor a um nome estático para acesso.
    # O servidor é vinculado com o metadado "Server" para diferenciar dos "Clients"
    nameServer.register('servidor.relogio', uri, metadata={"Server"})
    print("Novo registro no servidor de nomes:")
    print(nameServer.lookup('servidor.relogio', return_metadata=True))

    # Inicia a escuta de requisições do servidor
    threading.Thread(target=daemon.requestLoop).start()

    # Inicia a sincronização de relógios
    server = Pyro4.Proxy(nameServer.lookup('servidor.relogio'))
    msg = "Execução pausada para que sejam iniciados os clientes. Pressione 1 para adicionar um cliente por aqui " \
          "ou qualquer outro valor para realizar a sincronia de relógios\n"
    while input(msg) == '1':
        cliente.run_client(server.new_client_seq())

    # Recupera a lista de clientes
    clientes = nameServer.list(metadata_all={"Client"})
    print('Clientes no nameserver:')
    for cliente in clientes:
        print(cliente)

    # Inicia algoritimo de berkley para ajuste dos relógios
    print('Executando ajuste de relógios')
    server.berkeley(clientes)
