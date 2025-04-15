import socket
import threading
import json
import time
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
        self.room_id = None
        self.use_relay = False
        self.relay_connected = False
    
    def setup_network(self, is_host, peer_address=None, room_id=None, use_relay=False):
        # Garantir que não há conexões anteriores ativas
        self.close_connection()
        
        self.is_host = is_host
        self.peer_address = peer_address
        self.running = True
        self.is_connected = False
        self.room_id = room_id
        self.use_relay = use_relay
        self.relay_connected = False
        
        # Se estiver usando relay, não precisamos criar conexão P2P direta
        if use_relay:
            print(f"Usando relay para comunicação via servidor de salas (Room ID: {room_id})")
            
            # Configurar como conectado já que a comunicação será pelo servidor
            self.is_connected = True
            
            if is_host:
                print("Aguardando conexão do cliente via relay...")
                self.game.game_state = GameState.WAITING
            else:
                print("Conectado ao host via relay!")
                self.game.game_state = GameState.WAITING  # Cliente também espera confirmação
                
                # Enviar handshake
                handshake_msg = {'type': 'handshake', 'client': 'ready'}
                self.send_message(handshake_msg)
            
            return True
        
        # Se não usar relay, continua com a lógica normal de P2P
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Definir timeout para operações de socket
            if is_host:
                self.socket.settimeout(60)  # Timeout mais longo para hospedagem
            else:
                self.socket.settimeout(10)  # Timeout curto para conexão cliente
            
            if is_host:
                try:
                    self.socket.bind(('0.0.0.0', 5000))
                    self.socket.listen(1)
                    print("Waiting for opponent to connect...")
                    
                    # Iniciar thread de aceitação de conexão
                    self.connection_thread = threading.Thread(target=self.wait_for_connection)
                    self.connection_thread.daemon = True
                    self.connection_thread.start()
                    
                    # Host aguarda na tela de espera
                    self.game.game_state = GameState.WAITING
                except Exception as e:
                    print(f"Failed to host: {e}")
                    self.close_connection()
                    self.game.game_state = GameState.MENU
            else:
                if peer_address:
                    try:
                        print(f"Tentando conectar ao host: {peer_address}")
                        self.socket.connect((peer_address, 5000))
                        self.peer_socket = self.socket
                        self.is_connected = True
                        print("Connected to host!")
                        
                        # Cliente aguarda na tela de espera
                        self.game.game_state = GameState.WAITING
                        
                        # Enviar handshake
                        try:
                            handshake_msg = {'type': 'handshake', 'client': 'ready'}
                            self.send_message(handshake_msg)
                        except Exception as e:
                            print(f"Erro no handshake: {e}")
                            self.close_connection()
                            self.game.game_state = GameState.MENU
                            return
                        
                        # Start receiving messages
                        self.receive_thread = threading.Thread(target=self.receive_messages)
                        self.receive_thread.daemon = True
                        self.receive_thread.start()
                    except socket.timeout:
                        print("Connection attempt timed out")
                        self.close_connection()
                        self.game.game_state = GameState.MENU
                    except ConnectionRefusedError:
                        print("Connection refused by the host")
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
                
            # Configurar o socket para aceitar conexões
            self.socket.settimeout(None)  # sem timeout para accept()
            
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
            client_socket.settimeout(5.0)
            self.peer_socket = client_socket
            self.is_connected = True
            print(f"Client connected from {addr}")
            
            # Aguardar mensagem de handshake antes de iniciar o jogo
            try:
                data = client_socket.recv(1024)
                if data:
                    handshake = json.loads(data.decode('utf-8'))
                    if handshake.get('type') == 'handshake' and handshake.get('client') == 'ready':
                        print("Handshake recebido com sucesso")
                        # Enviar confirmação de handshake para o cliente
                        self.send_message({'type': 'handshake_ack', 'host': 'ready'})
                        # Agora sim iniciar o jogo
                        self.game.game_state = GameState.PLAYING
                        # Distribuir cartas iniciais
                        self.game.deal_initial_cards()
                    else:
                        print("Handshake inválido")
                        return
            except Exception as e:
                print(f"Erro no handshake: {e}")
                return
            
            # Iniciar thread de recebimento de mensagens
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
        except socket.timeout:
            print("Accept timed out, still waiting...")
            if self.running:
                pass
        except OSError as e:
            print(f"Error in wait_for_connection: {e}")
            if self.running and self.socket:
                self.game.game_state = GameState.MENU
        except Exception as e:
            print(f"Unexpected error in wait_for_connection: {e}")
            if self.running:
                self.game.game_state = GameState.MENU
    
    def handle_relay_message(self, message_data):
        """Processa mensagens recebidas via relay"""
        # Verificar tipo de mensagem de relay
        if message_data.get('type') == 'client_connected' and self.is_host:
            print("Cliente conectado via relay!")
            self.relay_connected = True
            self.game.game_state = GameState.PLAYING
            
            # Iniciar o jogo distribuindo cartas
            self.game.deal_initial_cards()
        
        elif message_data.get('type') == 'handshake':
            # Mensagem de handshake, confirmar conexão
            if self.is_host and message_data.get('client') == 'ready':
                print("Handshake cliente recebido via relay")
                self.relay_connected = True
        
        elif message_data.get('type') == 'game_state':
            # Estado do jogo do outro jogador (mão, status)
            self.game.handle_message(message_data)
        
        elif message_data.get('type') == 'host_left' or message_data.get('type') == 'client_left':
            print("O outro jogador desconectou")
            self.is_connected = False
            self.relay_connected = False
            self.game.game_state = GameState.MENU
        
        elif message_data.get('type') == 'restart_game':
            # Reiniciar jogo
            self.game.handle_message(message_data)
        
        elif message_data.get('type') == 'hit' or message_data.get('type') == 'stand':
            # Ações do jogo
            self.game.handle_message(message_data)
    
    def send_message(self, message):
        if not self.is_connected:
            return False
            
        # Se estiver usando relay, enviar através do servidor de salas
        if self.use_relay:
            return self.send_via_relay(message)
            
        # Lógica normal P2P
        if not self.peer_socket:
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
    
    def send_via_relay(self, message):
        """Envia mensagem através do servidor de salas usando relay"""
        # Verificar se está conectado ao serviço de salas
        if not hasattr(self.game, 'room_client') or not self.game.room_client.connected:
            print("Não está conectado ao servidor de salas")
            return False
            
        # Verificar se tem ID da sala
        if not self.room_id:
            print("Sem ID de sala para relay")
            return False
            
        try:
            # Preparar mensagem de relay
            relay_message = {
                'command': 'relay_message',
                'room_id': self.room_id,
                'data': message
            }
            
            # Enviar para o servidor de salas
            return self.game.room_client.send_message(relay_message)
        except Exception as e:
            print(f"Erro ao enviar via relay: {e}")
            return False
    
    def receive_messages(self):
        if not self.peer_socket and not self.use_relay:
            return
            
        # Se estiver usando relay, não precisa receber mensagens aqui
        # Elas são processadas pelo RoomClient 
        if self.use_relay:
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
        """Envia o estado atual do jogador para o outro jogador"""
        if not player:
            return
        
        try:
            hand_data = [{'value': card.value, 'suit': card.suit} for card in player.hand]
            message = {
                'type': 'game_state',
                'hand': hand_data,
                'status': player.status,
                'score': player.get_score() if hasattr(player, 'get_score') else 0
            }
            self.send_message(message)
        except Exception as e:
            print(f"Error sending game state: {e}")
    
    def close_connection(self):
        # Marcar como não executando para parar threads
        old_running = self.running
        self.running = False
        self.is_connected = False
        self.relay_connected = False
        
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

    def handle_message(self, message):
        """Processa mensagens recebidas do outro jogador"""
        msg_type = message.get('type')
        
        if msg_type == 'handshake_ack' and message.get('host') == 'ready':
            # Recebeu confirmação do handshake do host
            print("Handshake confirmado pelo host")
            self.game.game_state = GameState.PLAYING
            # Distribuir cartas iniciais para o cliente
            self.game.deal_initial_cards()
        elif msg_type == 'game_state':
            # Atualizar estado do jogo do outro jogador
            if 'hand' in message:
                self.game.remote_player.hand = [Card(card_data['value'], card_data['suit']) for card_data in message['hand']]
            if 'status' in message:
                self.game.remote_player.status = message['status']
        elif msg_type == 'host_left':
            # Host saiu do jogo
            print("O host saiu do jogo")
            self.close_connection()
            self.game.game_state = GameState.MENU
        elif msg_type == 'client_left':
            # Cliente saiu do jogo
            print("O cliente saiu do jogo")
            self.close_connection()
            self.game.game_state = GameState.MENU
        elif msg_type == 'restart_game':
            # Reiniciar o jogo
            self.game.deck = Deck()
            self.game.local_player = Player("You")
            self.game.remote_player = Player("Opponent")
            if not self.is_host:  # Apenas o cliente precisa distribuir cartas aqui
                self.game.deal_initial_cards()
        elif msg_type == 'hit':
            # Outro jogador pediu carta
            if self.is_host:  # Apenas o host processa hits
                card = self.game.deck.draw()
                if card:
                    self.game.remote_player.hand.append(card)
                    # Enviar estado atualizado
                    self.send_game_state(self.game.remote_player)
        elif msg_type == 'stand':
            # Outro jogador parou
            self.game.remote_player.status = "stand"

    def request_hit(self):
        """Solicita uma nova carta ao host"""
        if not self.is_host:
            self.send_message({'type': 'hit'})

    def send_stand(self):
        """Informa que o jogador parou"""
        self.send_message({'type': 'stand'})

    def send_restart_game(self):
        """Solicita reinício do jogo"""
        if self.is_host:
            self.send_message({'type': 'restart_game'}) 