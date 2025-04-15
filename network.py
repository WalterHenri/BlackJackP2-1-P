import socket
import threading
import json
import time
import urllib.request
from constants import GameState
from card import Card

class NetworkManager:
    def __init__(self, game):
        self.game = game
        self.socket = None
        self.peer_socket = None
        self.is_connected = False
        self.is_host = False
        self.peer_address = None
        self.running = True
        self.connection_thread = None
        self.receive_thread = None
        self.port = 5000  # Porta padrão
    
    def get_local_ip(self):
        """Tenta obter um IP local que seja acessível na rede"""
        try:
            # Tenta conectar a um serviço externo para determinar a interface de rede ativa
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"IP local detectado: {local_ip}")
            return local_ip
        except:
            # Fallback para o hostname local
            try:
                local_ip = socket.gethostbyname(socket.gethostname())
                print(f"IP do hostname: {local_ip}")
                return local_ip
            except:
                print("Não foi possível determinar o IP local, usando 127.0.0.1")
                return "127.0.0.1"
    
    def get_public_ip(self):
        """Tenta obter o IP público (só funciona se tiver acesso à internet)"""
        try:
            public_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
            print(f"IP público detectado: {public_ip}")
            return public_ip
        except:
            print("Não foi possível obter o IP público")
            return None
    
    def setup_network(self, is_host, peer_address=None):
        # Garantir que não há conexões anteriores ativas
        self.close_connection()
        
        self.is_host = is_host
        self.peer_address = peer_address
        self.running = True
        self.is_connected = False
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Definir timeout para operações de socket
            if is_host:
                # Sem timeout para o host durante o accept
                self.socket.settimeout(None)
            else:
                # Timeout mais curto para o cliente durante a conexão
                self.socket.settimeout(15)  # Aumentado para 15 segundos
            
            if is_host:
                try:
                    # Bind em todas as interfaces
                    print(f"Tentando hospedar na porta {self.port}...")
                    self.socket.bind(('0.0.0.0', self.port))
                    self.socket.listen(1)
                    
                    # Informar o IP local (para conexões na mesma rede)
                    local_ip = self.get_local_ip()
                    print(f"Host pronto. Outros jogadores na mesma rede podem se conectar usando: {local_ip}:{self.port}")
                    
                    # Tentar informar o IP público (para conexões pela internet)
                    public_ip = self.get_public_ip()
                    if public_ip:
                        print(f"Se seu roteador estiver configurado, jogadores de fora da rede podem usar: {public_ip}:{self.port}")
                        print("IMPORTANTE: É necessário abrir/encaminhar a porta no roteador para conexões externas.")
                    
                    print("Waiting for opponent to connect...")
                    
                    # Iniciar thread de aceitação de conexão
                    self.connection_thread = threading.Thread(target=self.wait_for_connection)
                    self.connection_thread.daemon = True
                    self.connection_thread.start()
                except Exception as e:
                    print(f"Failed to host: {e}")
                    self.close_connection()
                    self.game.game_state = GameState.MENU
            else:
                if peer_address:
                    try:
                        print(f"Tentando conectar ao host: {peer_address}:{self.port}")
                        # Mostrar mais informações para diagnóstico
                        try:
                            print(f"Resolução de nome: {socket.gethostbyname(peer_address)}")
                        except:
                            print(f"Não foi possível resolver o nome do host: {peer_address}")
                        
                        # Tentar conexão com timeout estendido
                        self.socket.settimeout(15)  # 15 segundos para timeout
                        self.socket.connect((peer_address, self.port))
                        self.peer_socket = self.socket
                        self.is_connected = True
                        print("Connected to host!")
                        
                        # Enviar mensagem de confirmação
                        try:
                            handshake_msg = {'type': 'handshake', 'client': 'ready'}
                            self.send_message(handshake_msg)
                        except Exception as e:
                            print(f"Erro no handshake: {e}")
                        
                        # Configurar timeout mais longo para operações de jogo
                        self.socket.settimeout(30)
                        
                        # Start receiving messages
                        self.receive_thread = threading.Thread(target=self.receive_messages)
                        self.receive_thread.daemon = True
                        self.receive_thread.start()
                        
                        # Start the game
                        self.game.game_state = GameState.PLAYING
                        
                        # Distribuir as cartas iniciais para o cliente também
                        self.game.deal_initial_cards()
                    except socket.timeout:
                        print("Connection attempt timed out. Verifique:")
                        print("1. O servidor está rodando e acessível")
                        print("2. O IP está correto")
                        print("3. A porta está aberta no firewall do servidor")
                        print("4. Se estiver conectando pela internet, o encaminhamento de porta está configurado no roteador")
                        self.close_connection()
                        self.game.game_state = GameState.MENU
                    except ConnectionRefusedError:
                        print("Connection refused by the host. O servidor pode não estar aceitando conexões.")
                        self.close_connection()
                        self.game.game_state = GameState.MENU
                    except Exception as e:
                        print(f"Failed to connect: {e}")
                        self.close_connection()
                        self.game.game_state = GameState.MENU
        except Exception as e:
            print(f"Error setting up network: {e}")
            self.close_connection()
            self.game.game_state = GameState.MENU
    
    def wait_for_connection(self):
        if not self.socket:
            print("Socket is not initialized")
            self.game.game_state = GameState.MENU
            return
            
        try:
            # Verificar se o socket ainda é válido
            if not self.running or not self.socket:
                return
            
            # Tentar aceitar conexão
            print("Aguardando conexão do cliente...")
            client_socket, addr = self.socket.accept()
            
            # Verificar se ainda estamos rodando após accept
            if not self.running:
                try:
                    client_socket.close()
                except:
                    pass
                return
                
            # Configurar o socket do cliente
            client_socket.settimeout(30.0)  # Timeout mais longo para o jogo
            self.peer_socket = client_socket
            self.is_connected = True
            print(f"Client connected from {addr}")
            
            # Aguardar mensagem de handshake antes de iniciar o jogo
            try:
                client_socket.settimeout(5.0)  # Timeout curto para o handshake
                data = client_socket.recv(1024)
                if data:
                    handshake = json.loads(data.decode('utf-8'))
                    if handshake.get('type') == 'handshake' and handshake.get('client') == 'ready':
                        print("Handshake recebido com sucesso")
                    else:
                        print("Handshake inválido, mas continuando")
                client_socket.settimeout(30.0)  # Voltar para timeout longo
            except Exception as e:
                print(f"Erro no handshake, mas continuando: {e}")
                client_socket.settimeout(30.0)  # Garantir timeout longo mesmo com erro
            
            # Iniciar o jogo
            self.game.game_state = GameState.PLAYING
            
            # Distribuir cartas iniciais
            self.game.deal_initial_cards()
            
            # Iniciar thread de recebimento de mensagens
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
        except socket.timeout:
            print("Accept timed out, still waiting...")
            if self.running:
                # Não usar recursão para evitar stack overflow
                pass
        except OSError as e:
            print(f"Error in wait_for_connection: {e}")
            if self.running and self.socket:
                self.game.game_state = GameState.MENU
        except Exception as e:
            print(f"Unexpected error in wait_for_connection: {e}")
            if self.running:
                self.game.game_state = GameState.MENU
    
    def send_message(self, message):
        if not self.is_connected or not self.peer_socket:
            return False
            
        try:
            # Conversão para JSON com tratamento de erros
            try:
                data = json.dumps(message).encode('utf-8')
            except Exception as e:
                print(f"Error encoding JSON: {e}")
                return False
                
            # Enviar dados
            self.peer_socket.sendall(data)
            return True
        except ConnectionResetError:
            print("Connection was reset by peer")
            self.is_connected = False
            return False
        except BrokenPipeError:
            print("Connection broken (pipe error)")
            self.is_connected = False
            return False
        except Exception as e:
            print(f"Failed to send message: {e}")
            self.is_connected = False
            return False
    
    def receive_messages(self):
        if not self.peer_socket:
            return
            
        buffer = ""
        
        while self.running and self.is_connected:
            try:
                if not self.peer_socket:
                    print("Socket inválido, encerrando recebimento")
                    break
                
                # Receber dados
                try:
                    data = self.peer_socket.recv(1024)
                except socket.timeout:
                    continue
                except ConnectionResetError:
                    print("Connection reset during receive")
                    break
                except Exception as e:
                    print(f"Error receiving data: {e}")
                    break
                    
                if not data:
                    print("No data received, connection closed")
                    break
                
                # Decodificar dados
                try:
                    decoded_data = data.decode('utf-8')
                    buffer += decoded_data
                except UnicodeDecodeError as e:
                    print(f"Error decoding data: {e}")
                    buffer = ""  # Reset buffer on decode error
                    continue
                
                # Processar JSON do buffer
                while buffer:
                    try:
                        # Tentar carregar o JSON completo
                        message = json.loads(buffer)
                        self.game.handle_message(message)
                        buffer = ""  # Limpar buffer após processamento
                        break
                    except json.JSONDecodeError as e:
                        # Verificar se o erro é por dados incompletos ou inválidos
                        if "Extra data" in str(e):
                            # Dados extras no buffer - encontrar o fim do primeiro JSON
                            pos = e.pos
                            try:
                                # Processar primeiro JSON e manter o resto no buffer
                                first_json = buffer[:pos]
                                message = json.loads(first_json)
                                self.game.handle_message(message)
                                buffer = buffer[pos:]  # Manter o resto para o próximo ciclo
                            except:
                                # Se falhar, descartar o buffer
                                print("Error processing partial JSON, discarding buffer")
                                buffer = ""
                        elif "Expecting value" in str(e) and len(buffer) < 1024:
                            # Provavelmente JSON incompleto, manter buffer e aguardar mais dados
                            break
                        else:
                            # JSON inválido, descartar buffer
                            print(f"Invalid JSON in buffer: {e}")
                            buffer = ""
                            break
                    except Exception as e:
                        print(f"Error processing message: {e}")
                        buffer = ""
                        break
                
            except Exception as e:
                print(f"Error in receive loop: {e}")
                break
        
        # Se saímos do loop, a conexão foi perdida
        self.is_connected = False
        
        # Se ainda estamos em execução, mas a conexão foi perdida, voltar ao menu
        if self.running:
            print("Connection lost, returning to menu")
            self.game.game_state = GameState.MENU
    
    def send_game_state(self, player):
        if not player:
            return
            
        try:
            hand_data = [{'value': card.value, 'suit': card.suit} for card in player.hand]
            message = {
                'type': 'game_state',
                'hand': hand_data,
                'status': player.status
            }
            self.send_message(message)
        except Exception as e:
            print(f"Error sending game state: {e}")
    
    def close_connection(self):
        # Marcar como não executando para parar threads
        old_running = self.running
        self.running = False
        self.is_connected = False
        
        # Fechar socket do peer (cliente conectado)
        if self.peer_socket and self.peer_socket != self.socket:
            try:
                self.peer_socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.peer_socket.close()
            except:
                pass
            self.peer_socket = None
        
        # Fechar socket principal (servidor/cliente principal)
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        # Aguardar término dos threads
        if old_running:
            time.sleep(0.5)  # Dar tempo para os threads terminarem 