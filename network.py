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
            self.socket.settimeout(30)  # 30 segundos de timeout
            
            if is_host:
                try:
                    self.socket.bind(('0.0.0.0', 5000))
                    self.socket.listen(1)
                    print("Waiting for opponent to connect...")
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
                        self.socket.connect((peer_address, 5000))
                        self.peer_socket = self.socket
                        self.is_connected = True
                        print("Connected to host!")
                        
                        # Start receiving messages
                        self.receive_thread = threading.Thread(target=self.receive_messages)
                        self.receive_thread.daemon = True
                        self.receive_thread.start()
                        
                        # Start the game
                        self.game.game_state = GameState.PLAYING
                        
                        # Distribuir as cartas iniciais para o cliente também
                        self.game.deal_initial_cards()
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
            # Configurar o socket para aceitar conexões com timeout
            self.socket.settimeout(None)  # sem timeout para accept()
            
            if self.running:
                client_socket, addr = self.socket.accept()
                
                if not self.running:  # Verificar novamente após accept() que pode ter bloqueado
                    try:
                        client_socket.close()
                    except:
                        pass
                    return
                    
                client_socket.settimeout(5.0)  # 5 segundos de timeout para operações de socket do cliente
                self.peer_socket = client_socket
                self.is_connected = True
                print(f"Client connected from {addr}")
                
                # Start the game
                self.game.game_state = GameState.PLAYING
                
                # Start dealing initial cards
                self.game.deal_initial_cards()
                
                # Start receiving messages
                self.receive_messages()
        except socket.timeout:
            print("Accept timed out, still waiting...")
            if self.running:
                self.wait_for_connection()  # Tentar novamente
        except OSError as e:
            print(f"Error in wait_for_connection: {e}")
            if self.running:
                self.game.game_state = GameState.MENU
        except Exception as e:
            print(f"Unexpected error in wait_for_connection: {e}")
            if self.running:
                self.game.game_state = GameState.MENU
    
    def send_message(self, message):
        if not self.is_connected or not self.peer_socket:
            return False
            
        try:
            data = json.dumps(message).encode('utf-8')
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
                    break
                
                # Receber dados com um buffer
                data = self.peer_socket.recv(1024)
                if not data:
                    print("No data received, connection closed")
                    break
                
                # Adicionar ao buffer e processar mensagens completas
                buffer += data.decode('utf-8')
                
                # Processar todas as mensagens no buffer
                try:
                    message = json.loads(buffer)
                    self.game.handle_message(message)
                    buffer = ""  # Limpar buffer após processamento bem-sucedido
                except json.JSONDecodeError:
                    # O buffer não contém uma mensagem JSON completa ainda, ou é inválido
                    pass
                except Exception as e:
                    print(f"Error processing message: {e}")
                    buffer = ""  # Limpar buffer em caso de erro
                
            except socket.timeout:
                # Timeout é normal, continuar o loop
                continue
            except ConnectionResetError:
                print("Connection was reset by peer")
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
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
        # Marcar como não executando para parar os threads
        self.running = False
        self.is_connected = False
        
        # Fechar socket do peer
        if self.peer_socket and self.peer_socket != self.socket:
            try:
                self.peer_socket.shutdown(socket.SHUT_RDWR)
                self.peer_socket.close()
            except:
                pass
            self.peer_socket = None
        
        # Fechar socket principal
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
        
        # Esperar que os threads terminem
        time.sleep(0.2)  # Pequena pausa para os threads terminarem 