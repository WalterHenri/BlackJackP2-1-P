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
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            self.running = True
            
            # Iniciar thread para receber mensagens
            self.receive_thread = threading.Thread(target=self.receive_messages)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
            return True
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
                self.socket.close()
            except:
                pass
        
        self.connected = False
        self.room_id = None
        self.is_host = False
    
    def set_callback(self, callback):
        """Define uma função de callback para processar mensagens recebidas"""
        self.callback = callback
    
    def receive_messages(self):
        """Recebe mensagens do servidor de salas"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    break
                
                message = json.loads(data.decode('utf-8'))
                
                # Processar mensagem
                if self.callback:
                    self.callback(message)
                
            except Exception as e:
                print(f"Erro ao receber mensagem: {e}")
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
            self.socket.sendall(json.dumps(message).encode('utf-8'))
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