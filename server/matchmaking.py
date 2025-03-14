import socket
import json
import time
import requests
from shared.network.message import Message, MessageType


class MatchmakingService:
    def __init__(self, lobby_server_address="localhost", lobby_server_port=5556):
        self.lobby_server_address = lobby_server_address
        self.lobby_server_port = lobby_server_port

    def create_game(self, player_name, max_players=4):
        """Create a new game lobby"""
        try:
            # Connect to the lobby server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.lobby_server_address, self.lobby_server_port))

                # Send create lobby request
                request = {
                    "command": "CREATE_LOBBY",
                    "host_name": player_name,
                    "max_players": max_players
                }
                sock.send(json.dumps(request).encode('utf-8'))

                # Get response
                data = sock.recv(4096)
                response = json.loads(data.decode('utf-8'))

                if response["status"] == "success":
                    return True, response["game_id"], response["lobby"]
                else:
                    return False, None, response.get("message", "Unknown error")

        except Exception as e:
            return False, None, str(e)

    def list_games(self):
        """Get a list of available game lobbies"""
        try:
            # Connect to the lobby server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.lobby_server_address, self.lobby_server_port))

                # Send list lobbies request
                request = {
                    "command": "LIST_LOBBIES"
                }
                sock.send(json.dumps(request).encode('utf-8'))

                # Get response
                data = sock.recv(4096)
                response = json.loads(data.decode('utf-8'))

                if response["status"] == "success":
                    return True, response["lobbies"]
                else:
                    return False, response.get("message", "Unknown error")

        except Exception as e:
            return False, str(e)

    def join_game(self, game_id):
        """Join an existing game lobby"""
        try:
            # Connect to the lobby server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.lobby_server_address, self.lobby_server_port))

                # Send join lobby request
                request = {
                    "command": "JOIN_LOBBY",
                    "game_id": game_id
                }
                sock.send(json.dumps(request).encode('utf-8'))

                # Get response
                data = sock.recv(4096)
                response = json.loads(data.decode('utf-8'))

                if response["status"] == "success":
                    return True, response["lobby"]
                else:
                    return False, response.get("message", "Unknown error")

        except Exception as e:
            return False, str(e)

    def leave_game(self, game_id):
        """Leave a game lobby"""
        try:
            # Connect to the lobby server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.lobby_server_address, self.lobby_server_port))

                # Send leave lobby request
                request = {
                    "command": "LEAVE_LOBBY",
                    "game_id": game_id
                }
                sock.send(json.dumps(request).encode('utf-8'))

                # Get response
                data = sock.recv(4096)
                response = json.loads(data.decode('utf-8'))

                if response["status"] == "success":
                    return True, "Successfully left the lobby"
                else:
                    return False, response.get("message", "Unknown error")

        except Exception as e:
            return False, str(e)

    def update_lobby(self, game_id, current_players):
        """Update lobby information"""
        try:
            # Connect to the lobby server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((self.lobby_server_address, self.lobby_server_port))

                # Send update lobby request
                request = {
                    "command": "UPDATE_LOBBY",
                    "game_id": game_id,
                    "current_players": current_players
                }
                sock.send(json.dumps(request).encode('utf-8'))

                # Get response
                data = sock.recv(4096)
                response = json.loads(data.decode('utf-8'))

                if response["status"] == "success":
                    return True, response["lobby"]
                else:
                    return False, response.get("message", "Unknown error")

        except Exception as e:
            return False, str(e)