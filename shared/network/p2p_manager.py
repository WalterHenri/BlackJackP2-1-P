import socket
import threading
import json
import uuid
import time
import logging
from shared.network.message import Message, MessageType
from shared.network.serializer import Serializer
from shared.network.nat_helper import NATHelper

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('P2PManager')

class P2PManager:
    def __init__(self, host=True, port=5555, relay_server=None, stun_server='stun.l.google.com:19302'):
        self.host = host
        self.port = port
        self.socket = None
        self.connections = {}  # player_id -> connection
        self.is_running = False
        self.player_id = str(uuid.uuid4())
        self.on_message_callbacks = []
        self.on_connection_callbacks = []
        self.on_disconnection_callbacks = []
        self.message_queue = []  # Queue for pending messages
        
        # Adicionar suporte a NAT
        self.nat_helper = NATHelper(stun_server=stun_server, relay_server=relay_server)
        self.public_address = None
        self.relay_mode = False
        self.relay_token = None

    def start(self):
        """Start the P2P network manager"""
        # Descobrir endereço público
        success, public_address, nat_type = self.nat_helper.discover_public_address()
        if success:
            self.public_address = public_address
            logger.info(f"Endereço público: {public_address}, tipo de NAT: {nat_type}")
        else:
            logger.warning("Não foi possível descobrir o endereço público")
            
        if self.host:
            self._start_host()
        self.is_running = True

    def _start_host(self):
        """Start as a host/server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind(('0.0.0.0', self.port))
            self.socket.listen(5)
            
            logger.info(f"Servidor P2P iniciado na porta {self.port}")
            
            # Start accepting connections in a separate thread
            threading.Thread(target=self._accept_connections, daemon=True).start()
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor P2P: {e}")
            raise e

    def connect_to_host(self, host_address):
        """Connect to a host as a client"""
        try:
            # Extrair host e porta
            host_ip, host_port_str = host_address.split(':')
            host_port = int(host_port_str)
            
            logger.info(f"Tentando conectar a {host_address}")
            
            # Verificar se podemos conectar diretamente
            direct_connection = self.nat_helper.check_direct_connectivity(host_address)
            
            if direct_connection:
                # Conexão direta é possível
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.connect((host_ip, host_port))
                
                # Enviar mensagem de identificação
                join_msg = Message.create_join_request(self.player_id, "Player")
                self.socket.send(join_msg.to_json().encode('utf-8'))
                
                # Start receiving messages from host
                conn_thread = threading.Thread(target=self._handle_connection, args=(self.socket, "host"), daemon=True)
                conn_thread.start()
                
                logger.info(f"Conectado diretamente a {host_address}")
                return True, "Conectado ao host"
            else:
                # Tentativa de hole punching
                logger.info(f"Tentando hole punching para {host_address}")
                punched = self.nat_helper.punch_hole(host_address)
                
                if punched:
                    # Agora tente a conexão novamente
                    time.sleep(1)  # Pequena pausa para NAT estabelecer regras
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.connect((host_ip, host_port))
                    
                    # Enviar mensagem de identificação
                    join_msg = Message.create_join_request(self.player_id, "Player")
                    self.socket.send(join_msg.to_json().encode('utf-8'))
                    
                    # Start receiving messages from host
                    conn_thread = threading.Thread(target=self._handle_connection, args=(self.socket, "host"), daemon=True)
                    conn_thread.start()
                    
                    logger.info(f"Conectado após hole punching a {host_address}")
                    return True, "Conectado ao host após hole punching"
                else:
                    # Se temos um servidor de relay, tente usá-lo
                    if self.nat_helper.relay_server:
                        logger.info(f"Tentando usar relay para {host_address}")
                        success, token = self.nat_helper.request_relay(self.player_id, "host")
                        
                        if success:
                            self.relay_mode = True
                            self.relay_token = token
                            # A conexão real seria estabelecida pelo servidor de relay
                            logger.info(f"Usando relay para conectar a {host_address}")
                            return True, "Conectado ao host através de relay"
                    
                    logger.error(f"Não foi possível conectar a {host_address}")
                    return False, f"Falha ao conectar"

        except Exception as e:
            logger.error(f"Erro ao conectar: {str(e)}")
            return False, f"Falha ao conectar: {str(e)}"

    def _accept_connections(self):
        """Accept incoming connections (host only)"""
        while self.is_running:
            try:
                client_socket, address = self.socket.accept()
                logger.info(f"Nova conexão de {address}")
                
                # Start a new thread to handle this connection
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, None),
                    daemon=True
                )
                conn_thread.start()
            except Exception as e:
                logger.error(f"Erro ao aceitar conexão: {str(e)}")
                time.sleep(0.1)

    def _handle_connection(self, client_socket, player_id=None):
        """Handle a client connection"""
        try:
            # Wait for identification message if player_id not yet known
            if not player_id:
                data = client_socket.recv(4096)
                if not data:
                    return

                message = Message.from_json(data.decode('utf-8'))
                if message.msg_type == MessageType.JOIN_REQUEST:
                    player_id = message.content["player_id"]
                    player_data = message.content

                    # Notify callbacks about new connection
                    for callback in self.on_connection_callbacks:
                        callback(player_id, player_data)
                    
                    logger.info(f"Jogador {player_id} conectado")

            # Add connection to our map
            self.connections[player_id] = client_socket

            # Continue receiving messages
            while self.is_running:
                try:
                    data = client_socket.recv(4096)
                    if not data:
                        break

                    message = Message.from_json(data.decode('utf-8'))
                    # Add message to queue instead of processing immediately
                    self.message_queue.append((player_id, message))
                except ConnectionResetError:
                    logger.warning(f"Conexão com {player_id} foi resetada")
                    break
                except Exception as e:
                    logger.error(f"Erro ao receber mensagem de {player_id}: {e}")
                    break

        except Exception as e:
            logger.error(f"Erro ao manipular conexão: {str(e)}")
        finally:
            # Handle disconnection
            if player_id and player_id in self.connections:
                del self.connections[player_id]
                logger.info(f"Jogador {player_id} desconectado")

                # Notify callbacks about disconnection
                for callback in self.on_disconnection_callbacks:
                    callback(player_id)

    def send_message(self, message, player_id=None):
        """Send a message to a specific player or all connected players"""
        if self.relay_mode and self.nat_helper.relay_server:
            # No modo relay, enviar pelo servidor de relay
            return self._send_via_relay(message, player_id)
            
        message_json = message.to_json()

        if player_id and player_id in self.connections:
            # Send to specific player
            try:
                self.connections[player_id].send(message_json.encode('utf-8'))
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar para {player_id}: {str(e)}")
                if player_id in self.connections:
                    del self.connections[player_id]
                    # Notify disconnection
                    for callback in self.on_disconnection_callbacks:
                        callback(player_id)
                return False
        elif player_id is None:
            # Send to all connected players
            failed_connections = []
            for pid, conn in list(self.connections.items()):
                try:
                    conn.send(message_json.encode('utf-8'))
                except Exception as e:
                    logger.error(f"Erro ao enviar broadcast para {pid}: {str(e)}")
                    failed_connections.append(pid)
            
            # Remover conexões falhas e notificar
            for pid in failed_connections:
                if pid in self.connections:
                    del self.connections[pid]
                    # Notify disconnection
                    for callback in self.on_disconnection_callbacks:
                        callback(pid)
                        
            return len(failed_connections) < len(self.connections)
        else:
            return False
    
    def _send_via_relay(self, message, player_id=None):
        """Enviar mensagem através do servidor de relay"""
        try:
            import requests
            
            # Prepara os dados para o relay
            relay_data = {
                "token": self.relay_token,
                "source_id": self.player_id,
                "message": message.to_json()
            }
            
            if player_id:
                relay_data["target_id"] = player_id
            
            # Envia para o servidor de relay
            response = requests.post(
                f"{self.nat_helper.relay_server}/relay/send",
                json=relay_data,
                timeout=5
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Erro ao enviar via relay: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao usar relay: {e}")
            return False

    def register_message_callback(self, callback):
        """Register a callback for when messages are received"""
        self.on_message_callbacks.append(callback)

    def register_connection_callback(self, callback):
        """Register a callback for when new connections are established"""
        self.on_connection_callbacks.append(callback)

    def register_disconnection_callback(self, callback):
        """Register a callback for when connections are closed"""
        self.on_disconnection_callbacks.append(callback)

    def close(self):
        """Close all connections and stop the manager"""
        self.is_running = False

        # Close all connections
        for conn in self.connections.values():
            try:
                conn.close()
            except:
                pass

        # Close main socket
        if self.socket:
            try:
                self.socket.close()
            except:
                pass

        self.connections.clear()
        logger.info("P2P Manager encerrado")

    def update(self):
        """Process any pending network messages"""
        # Process any messages in the queue
        while self.message_queue:
            sender_id, message = self.message_queue.pop(0)
            for callback in self.on_message_callbacks:
                callback(sender_id, message)
                
    def get_connection_info(self):
        """Retorna informações sobre as conexões atuais"""
        return {
            "total_connections": len(self.connections),
            "connected_players": list(self.connections.keys()),
            "public_address": self.public_address,
            "relay_mode": self.relay_mode
        }