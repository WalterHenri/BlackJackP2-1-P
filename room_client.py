import socket
import json
import threading
import time

class RoomClient:
    def __init__(self, server_host='localhost', server_port=5001):
        self.server_host = server_host
        self.server_port = server_port
        self.socket = None
        self.connected = False
        self.room_id = None
        self.ping_thread = None
        self.is_host = False
        self.running = False
        self.callback = None
        
    def connect(self):
        """Conecta ao servidor de salas"""
        try:
            print(f"Tentando conectar ao servidor de salas: {self.server_host}:{self.server_port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # Timeout de 10 segundos para conexão
            self.socket.connect((self.server_host, self.server_port))
            self.socket.settimeout(30)  # Timeout mais longo após conectar
            self.connected = True
            self.running = True
            
            # Iniciar thread para receber mensagens
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            print("Conectado ao servidor de salas com sucesso")
            return True
        except socket.timeout:
            print(f"Timeout ao tentar conectar ao servidor de salas: {self.server_host}")
            self.connected = False
            return False
        except Exception as e:
            print(f"Erro ao conectar ao servidor de salas: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Desconecta do servidor de salas"""
        self.running = False
        
        if self.is_host and self.room_id:
            self.delete_room(self.room_id)
        
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except:
                pass
            try:
                self.socket.close()
            except:
                pass
        
        self.connected = False
        self.room_id = None
        self.is_host = False
        
        # Esperar threads terminarem
        time.sleep(0.3)
    
    def set_callback(self, callback):
        """Define uma função de callback para processar mensagens recebidas"""
        self.callback = callback
    
    def receive_messages(self):
        """Recebe mensagens do servidor de salas"""
        buffer = ""
        
        while self.running and self.connected:
            try:
                try:
                    data = self.socket.recv(1024)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"Erro ao receber dados: {e}")
                    break
                    
                if not data:
                    print("Conexão com o servidor de salas fechada")
                    break
                
                # Adicionar dados ao buffer
                try:
                    buffer += data.decode('utf-8')
                except UnicodeDecodeError:
                    print("Erro ao decodificar dados")
                    buffer = ""
                    continue
                
                # Processar mensagens no buffer
                try:
                    message = json.loads(buffer)
                    buffer = ""
                    
                    # Processar mensagem
                    if self.callback:
                        self.callback(message)
                except json.JSONDecodeError as e:
                    if "Extra data" in str(e):
                        # Processar primeira mensagem completa
                        pos = e.pos
                        try:
                            first_json = buffer[:pos]
                            message = json.loads(first_json)
                            if self.callback:
                                self.callback(message)
                            buffer = buffer[pos:]
                        except:
                            buffer = ""
                    elif len(buffer) > 4096:
                        # Buffer muito grande, provavelmente corrompido
                        buffer = ""
                    # Se for outro erro, provavelmente é um JSON incompleto
                    # então mantemos no buffer
                except Exception as e:
                    print(f"Erro ao processar mensagem: {e}")
                    buffer = ""
                
            except Exception as e:
                print(f"Erro na thread de recebimento: {e}")
                break
        
        if self.running:
            print("Conexão com o servidor de salas perdida")
            self.connected = False
    
    def send_message(self, message):
        """Envia uma mensagem para o servidor de salas"""
        if not self.connected:
            print("Não conectado ao servidor de salas")
            return False
        
        try:
            data = json.dumps(message).encode('utf-8')
            self.socket.sendall(data)
            return True
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
            self.connected = False
            return False
    
    def list_rooms(self):
        """Solicita a lista de salas disponíveis"""
        message = {'command': 'list_rooms'}
        return self.send_message(message)
    
    def create_room(self, room_name, host_ip):
        """Cria uma nova sala"""
        message = {
            'command': 'create_room',
            'room_name': room_name,
            'host_ip': host_ip
        }
        
        if self.send_message(message):
            self.is_host = True
            
            # Iniciar thread de ping se ainda não estiver rodando
            if not self.ping_thread or not self.ping_thread.is_alive():
                self.ping_thread = threading.Thread(target=self.ping_room_loop)
                self.ping_thread.daemon = True
                self.ping_thread.start()
            
            return True
        return False
    
    def join_room(self, room_id):
        """Solicita entrada em uma sala"""
        message = {
            'command': 'join_room',
            'room_id': room_id
        }
        return self.send_message(message)
    
    def ping_room(self, room_id):
        """Envia ping para manter a sala ativa"""
        message = {
            'command': 'ping_room',
            'room_id': room_id
        }
        return self.send_message(message)
    
    def ping_room_loop(self):
        """Loop que envia pings periódicos para manter a sala ativa"""
        while self.running and self.connected and self.room_id and self.is_host:
            self.ping_room(self.room_id)
            time.sleep(30)  # Ping a cada 30 segundos
    
    def delete_room(self, room_id):
        """Solicita a exclusão de uma sala"""
        message = {
            'command': 'delete_room',
            'room_id': room_id
        }
        return self.send_message(message)
    
    def set_room_id(self, room_id):
        """Define o ID da sala atual"""
        self.room_id = room_id
        
        # Se for host, iniciar thread de ping
        if self.is_host and not self.ping_thread:
            self.ping_thread = threading.Thread(target=self.ping_room_loop)
            self.ping_thread.daemon = True
            self.ping_thread.start() 