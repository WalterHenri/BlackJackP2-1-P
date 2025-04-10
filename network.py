import socket
import threading
import json
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
    
    def setup_network(self, is_host, peer_address=None):
        self.is_host = is_host
        self.peer_address = peer_address
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.is_connected = False
        
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
                except Exception as e:
                    print(f"Failed to connect: {e}")
                    self.game.game_state = GameState.MENU
    
    def wait_for_connection(self):
        client_socket, addr = self.socket.accept()
        self.peer_socket = client_socket
        self.is_connected = True
        print(f"Client connected from {addr}")
        
        # Start the game
        self.game.game_state = GameState.PLAYING
        
        # Start dealing initial cards
        self.game.deal_initial_cards()
        
        # Start receiving messages
        self.receive_messages()
    
    def send_message(self, message):
        try:
            # Converte a mensagem para JSON e codifica
            message_bytes = json.dumps(message).encode('utf-8')
            # Adiciona o tamanho da mensagem como cabeçalho (4 bytes em formato de inteiro)
            message_length = len(message_bytes)
            header = message_length.to_bytes(4, byteorder='big')
            
            # Envia primeiro o cabeçalho, depois a mensagem
            self.peer_socket.sendall(header + message_bytes)
            print(f"Mensagem enviada: {message.get('type', 'unknown')} ({message_length} bytes)")
        except Exception as e:
            print(f"Falha ao enviar mensagem: {e}")
            self.is_connected = False
    
    def receive_messages(self):
        """Recebe e processa mensagens do outro jogador"""
        while self.is_connected:
            try:
                # Primeiro recebe o cabeçalho com o tamanho da mensagem
                header = self.peer_socket.recv(4)
                if not header or len(header) != 4:
                    print("Conexão fechada ou cabeçalho inválido")
                    break
                
                # Converte o cabeçalho para inteiro
                message_length = int.from_bytes(header, byteorder='big')
                
                # Recebe a mensagem completa baseada no tamanho do cabeçalho
                data = b''
                bytes_received = 0
                
                while bytes_received < message_length:
                    chunk = self.peer_socket.recv(min(1024, message_length - bytes_received))
                    if not chunk:
                        print("Conexão fechada durante recebimento de mensagem")
                        break
                    data += chunk
                    bytes_received += len(chunk)
                
                if bytes_received < message_length:
                    print(f"Mensagem incompleta recebida: {bytes_received}/{message_length} bytes")
                    break
                
                # Decodifica a mensagem
                message = json.loads(data.decode('utf-8'))
                print(f"Mensagem recebida: {message.get('type', 'unknown')} ({message_length} bytes)")
                
                # Processa a mensagem no thread principal
                self.game.handle_message(message)
            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar mensagem JSON: {e}")
            except ConnectionResetError:
                print("Conexão reiniciada pelo par")
                self.is_connected = False
                break
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
                self.is_connected = False
                break
        
        print("Loop de recebimento de mensagens encerrado")
        if self.game.game_state == GameState.PLAYING:
            # Voltar para o menu se a conexão cair durante o jogo
            self.game.game_state = GameState.MENU
    
    def send_game_state(self, player):
        hand_data = [{'value': card.value, 'suit': card.suit} for card in player.hand]
        message = {
            'type': 'game_state',
            'hand': hand_data,
            'status': player.status
        }
        self.send_message(message)
    
    def close_connection(self):
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        self.socket = None
        self.peer_socket = None 