import socket
import threading
import json
import uuid
import time
from shared.network.message import Message, MessageType
from shared.network.serializer import Serializer


class P2PManager:
    def __init__(self, host=True, port=5555):
        self.host = host
        self.port = port
        self.socket = None
        self.connections = {}  # player_id -> connection
        self.is_running = False
        self.player_id = str(uuid.uuid4())
        self.on_message_callbacks = []
        self.on_connection_callbacks = []
        self.on_disconnection_callbacks = []

    def start(self):
        """Start the P2P network manager"""
        if self.host:
            self._start_host()
        self.is_running = True

    def _start_host(self):
        """Start as a host/server"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', self.port))
        self.socket.listen(5)

        # Start accepting connections in a separate thread
        threading.Thread(target=self._accept_connections, daemon=True).start()

    def connect_to_host(self, host_address):
        """Connect to a host as a client"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host_address, self.port))

            # Start receiving messages from host
            conn_thread = threading.Thread(target=self._handle_connection, args=(self.socket, "host"), daemon=True)
            conn_thread.start()

            return True, "Connected to host"
        except Exception as e:
            return False, f"Failed to connect: {str(e)}"

    def _accept_connections(self):
        """Accept incoming connections (host only)"""
        while self.is_running:
            try:
                client_socket, address = self.socket.accept()
                # Start a new thread to handle this connection
                conn_thread = threading.Thread(
                    target=self._handle_connection,
                    args=(client_socket, None),
                    daemon=True
                )
                conn_thread.start()
            except Exception as e:
                print(f"Error accepting connection: {str(e)}")
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

                    # Notify callbacks about new connection
                    for callback in self.on_connection_callbacks:
                        callback(player_id, message.content)

            # Add connection to our map
            self.connections[player_id] = client_socket

            # Continue receiving messages
            while self.is_running:
                data = client_socket.recv(4096)
                if not data:
                    break

                message = Message.from_json(data.decode('utf-8'))

                # Notify callbacks about message
                for callback in self.on_message_callbacks:
                    callback(player_id, message)

        except Exception as e:
            print(f"Error handling connection: {str(e)}")
        finally:
            # Handle disconnection
            if player_id and player_id in self.connections:
                del self.connections[player_id]

                # Notify callbacks about disconnection
                for callback in self.on_disconnection_callbacks:
                    callback(player_id)

    def send_message(self, message, player_id=None):
        """Send a message to a specific player or all connected players"""
        message_json = message.to_json()

        if player_id and player_id in self.connections:
            # Send to specific player
            try:
                self.connections[player_id].send(message_json.encode('utf-8'))
                return True
            except Exception as e:
                print(f"Error sending to {player_id}: {str(e)}")
                return False
        elif player_id is None:
            # Send to all connected players
            for pid, conn in list(self.connections.items()):
                try:
                    conn.send(message_json.encode('utf-8'))
                except Exception as e:
                    print(f"Error broadcasting to {pid}: {str(e)}")
                    del self.connections[pid]
            return True
        else:
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