import socket
import csv
import os
import time

# --- Configurações ---
UDP_IP = "192.168.137.1"  # O IP do SEU PC (para onde o ESP32 envia dados)
UDP_PORT_DATA = 4210     # Porta que o Python escuta dados do ESP32
ESP32_IP = "192.168.137.155" # IP do seu ESP32! (Verifique no Serial Monitor do ESP32)
ESP32_COMMAND_PORT = 4211 # Porta que o ESP32 está escutando comandos

CSV_FILENAME = "dados_esp32_012.csv"
ACQUISITION_DURATION_SECONDS = 20 # Duração da aquisição que VOCÊ QUER ENVIAR para o ESP32

def setup_csv_file():
    """
    Prepara o arquivo CSV para a gravação dos dados recebidos do ESP32.
    
    Esta função é responsável por garantir que o arquivo CSV, cujo nome é definido
    pela variável global `CSV_FILENAME`, esteja pronto para receber os dados.
    
    Comportamento:
    1.  Verifica se o arquivo `CSV_FILENAME` já existe no diretório atual.
    2.  Se o arquivo **não existe**:
        - Ele é criado.
        - Uma linha de cabeçalho é escrita na primeira linha do arquivo.
          Os cabeçalhos são: 'Tempo_ms', 'Tensao', 'Corrente', 'Rotacao'.
        - Uma mensagem informativa é impressa no console, indicando que o
          arquivo foi criado com o cabeçalho.
    3.  Se o arquivo **já existe**:
        - Nenhuma alteração é feita no conteúdo existente do arquivo.
        - Novas linhas de dados serão simplesmente anexadas ao final do arquivo
          quando a função `main` começar a receber e salvar dados.
        - Uma mensagem informativa é impressa no console, indicando que novas
          linhas serão adicionadas ao arquivo existente.
    
    O arquivo é aberto no modo de anexar ('a'), e `newline=''` é usado para
    prevenir problemas de linhas em branco extras que podem ocorrer em diferentes
    sistemas operacionais ao trabalhar com arquivos CSV.
    
    Não recebe argumentos.
    Não retorna nenhum valor.
    """
    file_exists = os.path.isfile(CSV_FILENAME)
    with open(CSV_FILENAME, 'a', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        if not file_exists:
            csv_writer.writerow(['Tempo_ms', 'Tensao', 'Corrente', 'Rotacao'])
            print(f"Arquivo '{CSV_FILENAME}' criado com cabeçalho.")
        else:
            print(f"Arquivo '{CSV_FILENAME}' já existe. Novas linhas serão adicionadas.")

def send_command_to_esp32(command):
    """
    Envia um comando via protocolo UDP (User Datagram Protocol) para o módulo ESP32.

    Esta função estabelece uma comunicação unidirecional para enviar instruções
    ao ESP32. Ela cria um socket UDP temporário para cada comando enviado.

    Processo:
    1.  Cria um novo socket UDP (`socket.AF_INET` para IPv4, `socket.SOCK_DGRAM` para UDP).
    2.  Tenta enviar a string do comando (`command`) para o endereço IP e porta
        especificados nas variáveis globais `ESP32_IP` e `ESP32_COMMAND_PORT`.
        A string do comando é codificada para bytes usando UTF-8 antes do envio.
    3.  Em caso de sucesso, uma mensagem é impressa no console confirmando o envio
        do comando e o destino.
    4.  Em caso de falha durante o envio (por exemplo, problemas de rede, ESP32
        não acessível), uma exceção é capturada e uma mensagem de erro é impressa.
    5.  Independentemente do sucesso ou falha, o socket de comando é sempre fechado
        no bloco `finally`, garantindo a liberação dos recursos de rede.

    Args:
        command (str): A string do comando a ser enviada. Exemplos de comandos
                       esperados pelo ESP32 podem ser:
                       - "START_ACQUISITION:20000" (inicia aquisição por 20 segundos)
                       - "STOP_ACQUISITION" (interrompe a aquisição)

    Não retorna nenhum valor.
    """
    sock_command = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # UDP
    try:
        sock_command.sendto(command.encode('utf-8'), (ESP32_IP, ESP32_COMMAND_PORT))
        print(f"Comando '{command}' enviado para ESP32 em {ESP32_IP}:{ESP32_COMMAND_PORT}")
    except Exception as e:
        print(f"Erro ao enviar comando para o ESP32: {e}")
    finally:
        sock_command.close()

def main():
    """
    Função principal do script, responsável por gerenciar a comunicação UDP
    com o ESP32 e a gravação dos dados em um arquivo CSV.
    
    Esta função coordena todo o fluxo de trabalho do programa:
    
    1.  **Validação Inicial do IP do ESP32**:
        - Verifica se a variável global `ESP32_IP` ainda contém o endereço IP
          fictício de exemplo. Se sim, imprime um aviso crítico no console,
          lembrando o usuário de configurar o IP real do seu ESP32.
          (Uma linha `return` comentada existe para, se descomentada, forçar
          a interrupção do script até que o IP seja corrigido).
    
    2.  **Configuração do Socket de Dados para Recepção**:
        - Cria um socket UDP (`sock_data`) que será usado para receber os dados
          enviados pelo ESP32.
        - Vincula este socket ao endereço IP do PC (`UDP_IP`) e à porta de dados
          (`UDP_PORT_DATA`), tornando o script "escuta" por pacotes UDP nestes
          parâmetros.
        - Define um timeout de 1.0 segundo (`sock_data.settimeout(1.0)`) para as
          operações de recebimento. Isso evita que o script fique bloqueado
          indefinidamente esperando por dados, permitindo que o loop continue
          mesmo se não houver pacotes chegando.
    
    3.  **Preparação do Arquivo CSV**:
        - Chama a função `setup_csv_file()` para garantir que o arquivo CSV
          esteja devidamente configurado (criado com cabeçalho ou pronto para anexar).
    
    4.  **Envio do Comando de Início de Aquisição**:
        - Converte a `ACQUISITION_DURATION_SECONDS` (em segundos) para milissegundos.
        - Constrói a string do comando de início no formato
          "START_ACQUISITION:<duração_em_ms>".
        - Envia este comando ao ESP32 usando a função `send_command_to_esp32()`.
          O ESP32 é esperado para iniciar a coleta e transmissão de dados por
          essa duração.
    
    5.  **Loop Principal de Recepção e Processamento de Dados**:
        - Entra em um loop `while True` que continua indefinidamente até ser
          interrompido por um timeout de segurança, erro, ou interrupção do usuário.
        - **Timeout de Segurança do Python**:
            - A cada iteração, verifica se o tempo decorrido desde o início do
              script Python excedeu a duração da aquisição esperada do ESP32
              mais uma margem de 5 segundos. Se exceder, assume que o ESP32
              parou de enviar dados inesperadamente e encerra o loop.
        - **Recepção de Dados**:
            - Tenta receber um pacote UDP do ESP32 usando `sock_data.recvfrom(1024)`.
            - Decodifica os bytes recebidos para uma string UTF-8 e remove
              espaços em branco.
        - **Processamento da Mensagem**:
            - A mensagem recebida é esperada no formato:
              "Tempo_ms:VALOR,Tensao:VALOR,Corrente:VALOR,Rotacao:VALOR".
            - A string é dividida por vírgulas e cada parte é analisada para
              extrair os valores de `Tempo_ms` (int), `Tensao` (float),
              `Corrente` (float) e `Rotacao` (int).
            - Verifica se todos os valores foram extraídos com sucesso.
        - **Validação Opcional do Timestamp**:
            - Compara o `timestamp_esp32` recém-recebido com o `last_received_timestamp_esp32`.
            - Se o timestamp atual for menor ou igual ao anterior (e não for o
              primeiro pacote), imprime um aviso de "pacote fora de ordem ou duplicado".
              Isso é útil para depurar a comunicação UDP, que não garante ordem.
            - Atualiza `last_received_timestamp_esp32` com o timestamp atual.
        - **Gravação no CSV**:
            - Se a mensagem foi processada corretamente, os valores extraídos
              são escritos como uma nova linha no arquivo CSV.
        - **Tratamento de Erros no Loop**:
            - `except socket.timeout`: Captura a exceção quando nenhum dado é
              recebido dentro do timeout de 1 segundo. O `pass` permite que o
              loop continue sem travar.
            - `except Exception as e`: Captura quaisquer outros erros que possam
              ocorrer durante o processamento de uma mensagem (ex: formato
              inesperado). Imprime o erro e a mensagem bruta.
    
    6.  **Gerenciamento de Encerramento (try...except...finally)**:
        - `except KeyboardInterrupt`: Captura a interrupção do usuário (Ctrl+C),
          imprimindo uma mensagem de encerramento.
        - `except Exception as e`: Captura quaisquer erros gerais não tratados
          anteriormente que possam ocorrer fora do loop principal.
        - `finally`: Este bloco é **sempre** executado, garantindo uma finalização
          limpa do script:
            - Envia um comando "STOP_ACQUISITION" para o ESP32, instruindo-o
              a parar de transmitir dados.
            - Fecha o socket de dados (`sock_data.close()`), liberando a porta
              e os recursos de rede.
            - Imprime uma mensagem confirmando o fechamento do socket.
    
    Não recebe argumentos.
    Não retorna nenhum valor.
    """
    # Validação do IP do ESP32
    # if ESP32_IP == "192.168.137.155": # Este é o IP fictício do exemplo
    #     print("\nATENÇÃO: Por favor, substitua 'ESP32_IP' no código pelo IP real do seu ESP32 antes de rodar!")
    #     # return # Descomente essa linha para forçar você a mudar o IP

    # Socket para receber dados do ESP32
    sock_data = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock_data.bind((UDP_IP, UDP_PORT_DATA))
    sock_data.settimeout(1.0) # Timeout para não travar o loop de recebimento

    print(f"Escutando dados UDP em {UDP_IP}:{UDP_PORT_DATA}")
    setup_csv_file()

    # --- Enviar o comando de INÍCIO de aquisição com a duração ---
    duration_ms = ACQUISITION_DURATION_SECONDS * 1000 # Converte segundos para milissegundos
    start_command = f"START_ACQUISITION:{duration_ms}"
    send_command_to_esp32(start_command)

    # O script Python agora apenas espera os dados, o ESP32 controla a duração
    print(f"Aguardando dados do ESP32 por até {ACQUISITION_DURATION_SECONDS} segundos (controlado pelo ESP32)...")
    
    # Opcional: registrar o tempo de início do lado do Python para um timeout de segurança
    python_script_start_time = time.time()

    last_received_timestamp_esp32 = -1 # Para verificar a progressão do tempo do ESP32

    try:
        while True:
            # Timeout de segurança do lado do Python, caso o ESP32 pare de enviar inesperadamente
            if (time.time() - python_script_start_time) > (ACQUISITION_DURATION_SECONDS + 5): # +5s de margem
                print("\nAVISO: Tempo limite de espera do Python excedido. O ESP32 pode ter parado de enviar dados.")
                break

            try:
                data, addr = sock_data.recvfrom(1024) # Recebe dados do ESP32
                message = data.decode('utf-8').strip()

                # Processar a mensagem
                parts = message.split(',')
                timestamp_esp32 = None
                tensao = None
                corrente = None
                rotacao = None

                for part in parts:
                    if "Tempo_ms:" in part:
                        timestamp_esp32 = int(part.split(':')[1])
                    elif "Tensao:" in part:
                        tensao = float(part.split(':')[1])
                    elif "Corrente:" in part:
                        corrente = float(part.split(':')[1])
                    elif "Rotacao:" in part:
                        rotacao = int(part.split(':')[1])
                
                if timestamp_esp32 is not None and tensao is not None and corrente is not None and rotacao is not None:
                    # Opcional: verificar se o timestamp do ESP32 está progredindo
                    if timestamp_esp32 <= last_received_timestamp_esp32 and last_received_timestamp_esp32 != -1:
                        print(f"AVISO: Pacote fora de ordem ou duplicado: Tempo_ms={timestamp_esp32} (anterior={last_received_timestamp_esp32})")
                    last_received_timestamp_esp32 = timestamp_esp32

                    with open(CSV_FILENAME, 'a', newline='') as csvfile:
                        csv_writer = csv.writer(csvfile)
                        csv_writer.writerow([timestamp_esp32, tensao, corrente, rotacao])
                    # print(f"Salvo: Tempo_ms={timestamp_esp32}, Tensao={tensao:.2f}, Corrente={corrente:.2f}, Rotacao={rotacao}")
                else:
                    print(f"Aviso: Mensagem incompleta/malformada: '{message}'")

            except socket.timeout:
                print("Nenhum dado recebido no último segundo. Aguardando...")
                pass # Continua o loop para verificar o tempo limite ou se o ESP32 parou
            except Exception as e:
                print(f"Erro ao processar dados recebidos: {e}")
                print(f"Mensagem bruta que causou o erro: '{message}'")

    except KeyboardInterrupt:
        print("\nPrograma encerrado pelo usuário.")
    except Exception as e:
        print(f"Ocorreu um erro geral: {e}")
    finally:
        send_command_to_esp32("STOP_ACQUISITION") # Envia o comando STOP ao finalizar o script Python
        sock_data.close()
        print("Socket de dados fechado.")

if __name__ == "__main__":
    main()  
    # Este é um padrão comum em scripts Python. 
    # Garante que a função main() seja chamada apenas quando
    # o script é executado diretamente (e não quando é importado 
    # como um módulo em outro script)










