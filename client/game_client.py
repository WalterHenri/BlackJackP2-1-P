import pygame
import sys
import os
import json
import uuid
import time
from pygame.locals import *

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.player import Player
from shared.models.game import Game
from shared.network.message import Message, MessageType, ActionType
from shared.network.p2p_manager import P2PManager
from server.matchmaking import MatchmakingService

# Inicializar pygame
pygame.init()

# Cores
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 128, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)

# Configurações da tela
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
CARD_WIDTH = 100
CARD_HEIGHT = 150
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50


class BlackjackClient:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Blackjack 21 P2P")
        self.clock = pygame.time.Clock()

        # Estado do cliente
        self.player = None
        self.game = None
        self.p2p_manager = None
        self.matchmaking_service = MatchmakingService()
        self.game_state = None
        self.current_view = "menu"  # menu, lobby, game
        self.host_mode = False
        self.messages = []

        # Campos de entrada
        self.player_name = "Player"
        self.player_balance = 1000
        self.bet_amount = 100

        # Fontes
        self.title_font = pygame.font.SysFont("Arial", 48)
        self.large_font = pygame.font.SysFont("Arial", 36)
        self.medium_font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

    def start(self):
        """Iniciar o loop principal do jogo"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        # Fechar conexões
        if self.p2p_manager:
            self.p2p_manager.close()
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        """Lidar com eventos de entrada do usuário"""
        if self.current_view == "menu":
            self.handle_menu_event(event)
        elif self.current_view == "lobby":
            self.handle_lobby_event(event)
        elif self.current_view == "game":
            self.handle_game_event(event)

    def handle_menu_event(self, event):
        """Lidar com eventos na tela do menu"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de criar jogo
            if 100 <= mouse_pos[0] <= 300 and 300 <= mouse_pos[1] <= 350:
                self.create_game()

            # Botão de entrar em um jogo
            elif 100 <= mouse_pos[0] <= 300 and 400 <= mouse_pos[1] <= 450:
                self.join_game_screen()

    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de iniciar jogo (só para o host)
            if self.host_mode and 100 <= mouse_pos[0] <= 300 and 600 <= mouse_pos[1] <= 650:
                self.start_game()

            # Botão de voltar
            elif 100 <= mouse_pos[0] <= 300 and 700 <= mouse_pos[1] <= 750:
                self.leave_lobby()

    def handle_game_event(self, event):
        """Lidar com eventos durante o jogo"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Verificar se é nossa vez
            is_our_turn = (
                    self.game_state and
                    self.game_state["state"] == "PLAYER_TURN" and
                    self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
            )

            # Botão de Pedir Carta (Hit)
            if is_our_turn and 100 <= mouse_pos[0] <= 300 and 600 <= mouse_pos[1] <= 650:
                self.hit()

            # Botão de Parar (Stand)
            elif is_our_turn and 350 <= mouse_pos[0] <= 550 and 600 <= mouse_pos[1] <= 650:
                self.stand()

            # Botão de Apostar (na fase de apostas)
            elif (self.game_state and self.game_state["state"] == "BETTING" and
                  600 <= mouse_pos[0] <= 800 and 600 <= mouse_pos[1] <= 650):
                self.place_bet()

            # Botão de Nova Rodada (após o fim do jogo, apenas para o host)
            elif (self.host_mode and self.game_state and self.game_state["state"] == "GAME_OVER" and
                  600 <= mouse_pos[0] <= 800 and 700 <= mouse_pos[1] <= 750):
                self.new_round()

    def update(self):
        """Atualizar o estado do jogo"""
        pass

    def render(self):
        """Renderizar a interface do jogo"""
        self.screen.fill(GREEN)

        if self.current_view == "menu":
            self.render_menu()
        elif self.current_view == "lobby":
            self.render_lobby()
        elif self.current_view == "game":
            self.render_game()

        pygame.display.flip()

    def render_menu(self):
        """Renderizar a tela do menu"""
        # Título
        title = self.title_font.render("Blackjack 21 P2P", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        # Nome do jogador
        name_label = self.medium_font.render("Seu nome:", True, WHITE)
        self.screen.blit(name_label, (100, 200))

        name_box = pygame.Rect(300, 200, 300, 40)
        pygame.draw.rect(self.screen, WHITE, name_box)
        name_text = self.medium_font.render(self.player_name, True, BLACK)
        self.screen.blit(name_text, (310, 205))

        # Botões
        create_button = pygame.Rect(100, 300, 200, 50)
        pygame.draw.rect(self.screen, BLUE, create_button)
        create_text = self.medium_font.render("Criar Jogo", True, WHITE)
        self.screen.blit(create_text, (125, 310))

        join_button = pygame.Rect(100, 400, 200, 50)
        pygame.draw.rect(self.screen, BLUE, join_button)
        join_text = self.medium_font.render("Entrar em Jogo", True, WHITE)
        self.screen.blit(join_text, (105, 410))

    def render_lobby(self):
        """Renderizar a tela de lobby"""
        # Título
        title = self.title_font.render("Lobby", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))

        # ID do jogo
        if self.game:
            game_id_text = self.medium_font.render(f"ID do Jogo: {self.game.game_id}", True, WHITE)
            self.screen.blit(game_id_text, (100, 150))

        # Lista de jogadores
        players_title = self.large_font.render("Jogadores:", True, WHITE)
        self.screen.blit(players_title, (100, 200))

        y_pos = 250
        if self.game_state:
            for player in self.game_state["players"]:
                player_text = self.medium_font.render(
                    f"{player['name']} - Saldo: {player['balance']} " +
                    ("(Host)" if player["is_host"] else ""),
                    True, WHITE
                )
                self.screen.blit(player_text, (120, y_pos))
                y_pos += 40

        # Botões
        if self.host_mode:
            start_button = pygame.Rect(100, 600, 200, 50)
            pygame.draw.rect(self.screen, BLUE, start_button)
            start_text = self.medium_font.render("Iniciar Jogo", True, WHITE)
            self.screen.blit(start_text, (125, 610))

        back_button = pygame.Rect(100, 700, 200, 50)
        pygame.draw.rect(self.screen, RED, back_button)
        back_text = self.medium_font.render("Voltar", True, WHITE)
        self.screen.blit(back_text, (160, 710))

    def render_game(self):
        """Renderizar a tela do jogo"""
        if not self.game_state:
            return

        # Título e estado do jogo
        title = self.large_font.render(f"Blackjack 21 - {self.game_state['state']}", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 10))

        # Informações do jogador atual
        current_player_idx = self.game_state["current_player_index"]
        if current_player_idx < len(self.game_state["players"]):
            current_player = self.game_state["players"][current_player_idx]
            turn_text = self.medium_font.render(f"Turno de: {current_player['name']}", True, WHITE)
            self.screen.blit(turn_text, (SCREEN_WIDTH // 2 - turn_text.get_width() // 2, 50))

        # Cartas e informações dos jogadores
        player_count = len(self.game_state["players"])
        for i, player in enumerate(self.game_state["players"]):
            # Calcular posição para este jogador
            angle = (2 * 3.14159 * i) / player_count
            radius = min(SCREEN_WIDTH, SCREEN_HEIGHT) * 0.35
            center_x = SCREEN_WIDTH // 2
            center_y = SCREEN_HEIGHT // 2

            x = center_x + int(radius * 0.8 * -1 if i == 0 else 1)
            y = center_y - 100

            # Destacar o jogador atual
            highlight = pygame.Rect(x - 20, y - 20, CARD_WIDTH * 2 + 40, CARD_HEIGHT + 100)
            highlight_color = BLUE if player["id"] == self.player.player_id else GRAY
            pygame.draw.rect(self.screen, highlight_color, highlight, 2)

            # Nome e informações do jogador
            player_info = self.small_font.render(
                f"{player['name']} - Saldo: {player['balance']}" +
                (f" - Aposta: {player['current_bet']}" if player['current_bet'] > 0 else ""),
                True, WHITE
            )
            self.screen.blit(player_info, (x, y - 40))

            # Valor da mão
            hand_value = self.medium_font.render(
                f"Valor: {player['hand_value']}" +
                (" (Estouro!)" if player["is_busted"] else ""),
                True, RED if player["is_busted"] else WHITE
            )
            self.screen.blit(hand_value, (x, y + CARD_HEIGHT + 20))

            # Renderizar cartas
            for j, card in enumerate(player["cards"]):
                self.render_card(card, x + j * 40, y)

        # Cartas restantes no baralho
        deck_text = self.small_font.render(f"Cartas no baralho: {self.game_state['cards_remaining']}", True, WHITE)
        self.screen.blit(deck_text, (10, 10))

        # Botões de ação (baseados no estado do jogo)
        is_our_turn = (
                self.game_state["state"] == "PLAYER_TURN" and
                self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
        )

        # Botão de Pedir Carta (Hit)
        hit_button = pygame.Rect(100, 600, 200, 50)
        hit_color = BLUE if is_our_turn else GRAY
        pygame.draw.rect(self.screen, hit_color, hit_button)
        hit_text = self.medium_font.render("Pedir Carta", True, WHITE)
        self.screen.blit(hit_text, (130, 610))

        # Botão de Parar (Stand)
        stand_button = pygame.Rect(350, 600, 200, 50)
        stand_color = BLUE if is_our_turn else GRAY
        pygame.draw.rect(self.screen, stand_color, stand_button)
        stand_text = self.medium_font.render("Parar", True, WHITE)
        self.screen.blit(stand_text, (410, 610))

        # Botão de Apostar (na fase de apostas)
        if self.game_state["state"] == "BETTING":
            bet_button = pygame.Rect(600, 600, 200, 50)
            pygame.draw.rect(self.screen, BLUE, bet_button)
            bet_text = self.medium_font.render(f"Apostar {self.bet_amount}", True, WHITE)
            self.screen.blit(bet_text, (630, 610))

            # Controles para ajustar o valor da aposta
            bet_minus_button = pygame.Rect(550, 600, 40, 50)
            pygame.draw.rect(self.screen, RED, bet_minus_button)
            bet_minus_text = self.medium_font.render("-", True, WHITE)
            self.screen.blit(bet_minus_text, (565, 610))

            bet_plus_button = pygame.Rect(810, 600, 40, 50)
            pygame.draw.rect(self.screen, GREEN, bet_plus_button)
            bet_plus_text = self.medium_font.render("+", True, WHITE)
            self.screen.blit(bet_plus_text, (825, 610))

            # Botão de Nova Rodada (após o fim do jogo, apenas para o host)
        if self.host_mode and self.game_state["state"] == "GAME_OVER":
            new_round_button = pygame.Rect(600, 700, 200, 50)
            pygame.draw.rect(self.screen, BLUE, new_round_button)
            new_round_text = self.medium_font.render("Nova Rodada", True, WHITE)
            self.screen.blit(new_round_text, (630, 710))

            # Mensagens do jogo
        messages_box = pygame.Rect(10, SCREEN_HEIGHT - 150, SCREEN_WIDTH - 20, 140)
        pygame.draw.rect(self.screen, BLACK, messages_box, 2)

        message_y = SCREEN_HEIGHT - 140
        for msg in self.game_state["messages"][-5:]:  # Últimas 5 mensagens
            message_text = self.small_font.render(msg, True, WHITE)
            self.screen.blit(message_text, (20, message_y))
            message_y += 25

    def render_card(self, card, x, y):
        """Renderizar uma carta de baralho"""
        # Fundo da carta
        card_rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
        pygame.draw.rect(self.screen, WHITE, card_rect)
        pygame.draw.rect(self.screen, BLACK, card_rect, 2)

        # Determinar cor (vermelho para copas e ouros, preto para espadas e paus)
        suit = card["suit"]
        color = RED if suit in ["HEARTS", "DIAMONDS"] else BLACK

        # Símbolo do naipe
        suit_symbol = {
            "HEARTS": "♥",
            "DIAMONDS": "♦",
            "SPADES": "♠",
            "CLUBS": "♣"
        }.get(suit, "?")

        suit_text = self.large_font.render(suit_symbol, True, color)
        self.screen.blit(suit_text, (x + CARD_WIDTH // 2 - suit_text.get_width() // 2,
                                     y + CARD_HEIGHT // 2 - suit_text.get_height() // 2))

        # Valor da carta
        value = card["value"]
        if value == "ACE":
            display_value = "A"
        elif value == "JACK":
            display_value = "J"
        elif value == "QUEEN":
            display_value = "Q"
        elif value == "KING":
            display_value = "K"
        else:
            # Extrair o número do nome do enum (por exemplo, "TWO" -> "2")
            display_value = value.replace("TWO", "2").replace("THREE", "3").replace("FOUR", "4") \
                .replace("FIVE", "5").replace("SIX", "6").replace("SEVEN", "7") \
                .replace("EIGHT", "8").replace("NINE", "9").replace("TEN", "10")

        value_text = self.medium_font.render(display_value, True, color)
        self.screen.blit(value_text, (x + 5, y + 5))  # Canto superior esquerdo
        self.screen.blit(value_text, (x + CARD_WIDTH - value_text.get_width() - 5,
                                      y + CARD_HEIGHT - value_text.get_height() - 5))  # Canto inferior direito

    def create_game(self):
        """Criar um novo jogo como host"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
        self.game = Game()
        self.game.initialize_game(self.player)

        # Iniciar o servidor P2P
        self.p2p_manager = P2PManager(host=True)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.register_connection_callback(self.on_player_connected)
        self.p2p_manager.register_disconnection_callback(self.on_player_disconnected)
        self.p2p_manager.start()

        # Criar lobby no serviço de matchmaking
        success, game_id, lobby = self.matchmaking_service.create_game(self.player_name)
        if success:
            self.game.game_id = game_id
            self.current_view = "lobby"
            self.host_mode = True
            self.game_state = self.game.get_game_state()
        else:
            print(f"Erro ao criar lobby: {lobby}")

    def join_game_screen(self):
        """Mostrar tela para entrar em um jogo existente"""
        # Na implementação real, você pode adicionar uma tela para listar lobbies disponíveis
        # Simplificado para este exemplo
        success, lobbies = self.matchmaking_service.list_games()
        if success and lobbies:
            # Apenas entrar no primeiro lobby disponível para este exemplo
            self.join_game(lobbies[0]["game_id"])
        else:
            print("Nenhum jogo disponível")

    def join_game(self, game_id):
        """Entrar em um jogo existente"""
        self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))

        # Conectar ao lobby
        success, lobby = self.matchmaking_service.join_game(game_id)
        if not success:
            print(f"Erro ao entrar no lobby: {lobby}")
            return

        # Conectar ao host P2P
        host_address = lobby["host_address"]
        self.p2p_manager = P2PManager(host=False)
        self.p2p_manager.register_message_callback(self.on_message_received)
        self.p2p_manager.start()

        connect_success, message = self.p2p_manager.connect_to_host(host_address)
        if connect_success:
            # Enviar mensagem de solicitação para entrar
            join_message = Message.create_join_request(
                self.player.player_id,
                self.player.name
            )
            self.p2p_manager.send_message(join_message)

            self.current_view = "lobby"
            self.host_mode = False
        else:
            print(f"Erro ao conectar ao host: {message}")

    def on_message_received(self, sender_id, message):
        """Callback para mensagens recebidas"""
        if message.msg_type == MessageType.GAME_STATE:
            # Atualizar o estado do jogo
            self.game_state = message.content

            # Se o jogo começou, mudar para a view do jogo
            if self.game_state["state"] not in ["WAITING_FOR_PLAYERS"]:
                self.current_view = "game"

        elif message.msg_type == MessageType.JOIN_REQUEST and self.host_mode:
            # Processar solicitação de entrada (apenas o host)
            player_id = message.content["player_id"]
            player_name = message.content["player_name"]

            # Criar novo jogador e adicionar ao jogo
            new_player = Player(player_name, 1000, player_id)
            success, player_index = self.game.add_player(new_player)

            # Enviar resposta
            response = Message.create_join_response(
                self.player.player_id,
                success,
                self.game.game_id if success else None,
                "Jogo já iniciado" if not success else None
            )
            self.p2p_manager.send_message(response, player_id)

            # Atualizar lobby no matchmaking service
            player_list = [p.name for p in self.game.state_manager.players]
            self.matchmaking_service.update_lobby(self.game.game_id, player_list)

            # Enviar estado atualizado do jogo para todos
            self.broadcast_game_state()

        elif message.msg_type == MessageType.JOIN_RESPONSE and not self.host_mode:
            # Processar resposta de solicitação de entrada
            if message.content["accepted"]:
                print(f"Entrou no jogo {message.content['game_id']}")
            else:
                print(f"Falha ao entrar no jogo: {message.content['reason']}")
                self.current_view = "menu"

        elif message.msg_type == MessageType.PLAYER_ACTION:
            # Processar ação do jogador (apenas o host)
            if self.host_mode:
                self.process_player_action(sender_id, message.content)

    def on_player_connected(self, player_id, player_data):
        """Callback para quando um novo jogador se conecta"""
        print(f"Jogador conectado: {player_id}")

    def on_player_disconnected(self, player_id):
        """Callback para quando um jogador se desconecta"""
        print(f"Jogador desconectado: {player_id}")

        # Se somos o host, remover o jogador do jogo
        if self.host_mode and self.game:
            self.game.remove_player(player_id)
            self.broadcast_game_state()

    def process_player_action(self, player_id, action_data):
        """Processar uma ação de jogador (host)"""
        action_type = action_data["action_type"]
        action_data = action_data["action_data"]

        if action_type == ActionType.PLACE_BET:
            success, message = self.game.place_bet(player_id, action_data["amount"])
        elif action_type == ActionType.HIT:
            success, message = self.game.hit(player_id)
        elif action_type == ActionType.STAND:
            success, message = self.game.stand(player_id)
        else:
            success, message = False, "Ação desconhecida"

        # Adicionar mensagem ao jogo
        if success:
            self.game.messages.append(message)

        # Atualizar estado do jogo para todos
        self.broadcast_game_state()

    def broadcast_game_state(self):
        """Enviar o estado atual do jogo para todos os jogadores"""
        if self.host_mode and self.game:
            self.game_state = self.game.get_game_state()
            game_state_message = Message.create_game_state_message(
                self.player.player_id,
                self.game_state
            )
            self.p2p_manager.send_message(game_state_message)

    def hit(self):
        """Pedir mais uma carta"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            hit_message = Message.create_action_message(
                self.player.player_id,
                ActionType.HIT
            )
            self.p2p_manager.send_message(hit_message)
        else:
            # Host processa diretamente
            success, message = self.game.hit(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def stand(self):
        """Parar de pedir cartas"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            stand_message = Message.create_action_message(
                self.player.player_id,
                ActionType.STAND
            )
            self.p2p_manager.send_message(stand_message)
        else:
            # Host processa diretamente
            success, message = self.game.stand(self.player.player_id)
            if success:
                self.game.messages.append(message)
            self.broadcast_game_state()

    def place_bet(self):
        """Colocar uma aposta"""
        if not self.host_mode:
            # Cliente envia solicitação para o host
            bet_message = Message.create_action_message(
                self.player.player_id,
                ActionType.PLACE_BET,
                {"amount": self.bet_amount}
            )
            self.p2p_manager.send_message(bet_message)
        else:
            # Host processa diretamente
            success, message = self.game.place_bet(self.player.player_id, self.bet_amount)
            if success:
                self.game.messages.append(f"{self.player.name} apostou {self.bet_amount}")
            self.broadcast_game_state()

    def start_game(self):
        """Iniciar o jogo (apenas host)"""
        if not self.host_mode:
            return

        success, message = self.game.start_game()
        if success:
            self.game.messages.append("O jogo começou!")
            self.current_view = "game"
            self.broadcast_game_state()
        else:
            print(f"Erro ao iniciar o jogo: {message}")

    def new_round(self):
        """Iniciar uma nova rodada (apenas host)"""
        if not self.host_mode:
            return

        success, message = self.game.start_new_round()
        if success:
            self.game.messages.append("Nova rodada iniciada!")
            self.broadcast_game_state()
        else:
            print(f"Erro ao iniciar nova rodada: {message}")

    def leave_lobby(self):
        """Sair do lobby e voltar ao menu"""
        if self.p2p_manager:
            self.p2p_manager.close()
            self.p2p_manager = None

        if self.game and self.game.game_id:
            self.matchmaking_service.leave_game(self.game.game_id)

        self.game = None
        self.game_state = None
        self.current_view = "menu"
        self.host_mode = False

    def increase_bet(self):
        """Aumentar o valor da aposta"""
        self.bet_amount += 10
        if self.bet_amount > self.