import socket
import threading
import json
import time
import uuid
import sys

# Configurações do servidor
HOST = '0.0.0.0'
PORT = 5001
ROOM_CLEANUP_INTERVAL = 60  # Segundos antes de remover salas inativas

class RoomServer:
    def __init__(self):
        self.server_socket = None
        self.rooms = {}  # {room_id: {'host': host_ip, 'name': room_name, 'last_ping': timestamp}}
        self.clients = []  # Lista de sockets de clientes conectados
        self.running = False
        self.lock = threading.Lock()  # Para acesso seguro à lista de salas
    
    def start(self):
        """Inicia o servidor de salas"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((HOST, PORT))
            self.server_socket.listen(10)  # Máximo 10 conexões pendentes
            self.running = True
            
            print(f"Servidor de salas iniciado em {HOST}:{PORT}")
            
            # Iniciar thread para limpeza de salas inativas
            cleanup_thread = threading.Thread(target=self.cleanup_inactive_rooms)
            cleanup_thread.daemon = True
            cleanup_thread.start()
            
            # Aceitar conexões de clientes
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    print(f"Conexão recebida de {addr}")
                    
                    # Iniciar thread para cada cliente
                    client_thread = threading.Thread(target=self.handle_client, args=(client_socket, addr))
                    client_thread.daemon = True
                    client_thread.start()
                    
                except Exception as e:
                    if self.running:
                        print(f"Erro ao aceitar conexão: {e}")
                    else:
                        break
                
        except Exception as e:
            print(f"Erro ao iniciar servidor: {e}")
            self.stop()
    
    def stop(self):
        """Encerra o servidor de salas"""
        self.running = False
        
        # Fechar todas as conexões de clientes
        for client in self.clients:
            try:
                client.close()
            except:
                pass
        
        # Fechar socket do servidor
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Servidor de salas encerrado")
    
    def handle_client(self, client_socket, addr):
        """Gerencia comunicação com um cliente"""
        try:
            self.clients.append(client_socket)
            
            while self.running:
                data = client_socket.recv(1024)
                if not data:
                    break
                
                try:
                    message = json.loads(data.decode('utf-8'))
                    self.process_message(client_socket, addr, message)
                except json.JSONDecodeError:
                    print(f"Mensagem inválida de {addr}")
                
        except Exception as e:
            print(f"Erro na comunicação com {addr}: {e}")
        
        finally:
            # Remover cliente da lista
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            
            # Fechar socket
            try:
                client_socket.close()
            except:
                pass
            
            print(f"Conexão com {addr} encerrada")
    
    def process_message(self, client_socket, addr, message):
        """Processa mensagens recebidas de clientes"""
        command = message.get('command')
        
        if command == 'list_rooms':
            self.send_room_list(client_socket)
        
        elif command == 'create_room':
            room_name = message.get('room_name', 'Sala sem nome')
            host_ip = message.get('host_ip', addr[0])
            room_id = self.create_room(room_name, host_ip)
            
            response = {
                'command': 'room_created',
                'room_id': room_id,
                'room_name': room_name,
                'host_ip': host_ip
            }
            self.send_message(client_socket, response)
        
        elif command == 'join_room':
            room_id = message.get('room_id')
            with self.lock:
                if room_id in self.rooms:
                    response = {
                        'command': 'join_success',
                        'room_id': room_id,
                        'room_name': self.rooms[room_id]['name'],
                        'host_ip': self.rooms[room_id]['host']
                    }
                else:
                    response = {
                        'command': 'join_failed',
                        'reason': 'Sala não encontrada'
                    }
            self.send_message(client_socket, response)
        
        elif command == 'ping_room':
            room_id = message.get('room_id')
            with self.lock:
                if room_id in self.rooms:
                    self.rooms[room_id]['last_ping'] = time.time()
                    response = {'command': 'pong'}
                else:
                    response = {'command': 'room_not_found'}
            self.send_message(client_socket, response)
        
        elif command == 'delete_room':
            room_id = message.get('room_id')
            with self.lock:
                if room_id in self.rooms:
                    del self.rooms[room_id]
                    response = {'command': 'room_deleted'}
                else:
                    response = {'command': 'room_not_found'}
            self.send_message(client_socket, response)
    
    def send_message(self, client_socket, message):
        """Envia mensagem para um cliente"""
        try:
            client_socket.sendall(json.dumps(message).encode('utf-8'))
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")
    
    def send_room_list(self, client_socket):
        """Envia lista de salas disponíveis para um cliente"""
        with self.lock:
            room_list = [
                {
                    'id': room_id,
                    'name': room_info['name'],
                    'host': room_info['host']
                }
                for room_id, room_info in self.rooms.items()
            ]
        
        response = {
            'command': 'room_list',
            'rooms': room_list
        }
        
        self.send_message(client_socket, response)
    
    def create_room(self, room_name, host_ip):
        """Cria uma nova sala"""
        room_id = str(uuid.uuid4())[:8]  # ID único da sala (8 caracteres)
        
        with self.lock:
            self.rooms[room_id] = {
                'name': room_name,
                'host': host_ip,
                'last_ping': time.time()
            }
        
        print(f"Sala criada: {room_name} (ID: {room_id}, Host: {host_ip})")
        return room_id
    
    def cleanup_inactive_rooms(self):
        """Remove salas inativas (que não receberam ping por um tempo)"""
        while self.running:
            time.sleep(10)  # Verificar a cada 10 segundos
            
            current_time = time.time()
            rooms_to_remove = []
            
            with self.lock:
                for room_id, room_info in self.rooms.items():
                    # Se a última atualização foi há mais de ROOM_CLEANUP_INTERVAL segundos
                    if current_time - room_info['last_ping'] > ROOM_CLEANUP_INTERVAL:
                        rooms_to_remove.append(room_id)
                
                # Remover salas inativas
                for room_id in rooms_to_remove:
                    del self.rooms[room_id]
                    print(f"Sala removida por inatividade: {room_id}")

if __name__ == "__main__":
    server = RoomServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\nServidor encerrado pelo usuário")
    finally:
        server.stop()
        sys.exit(0) 