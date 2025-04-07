import pygame
import sys
import os
import uuid
import time
import math
from pygame.locals import *

# Adicione o diretório raiz ao path para importar os módulos compartilhados
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.models.player import Player
from shared.models.game import Game
from client.card_sprites import CardSprites
from client.player_data import get_player_balance, update_player_balance, check_player_eliminated
from client.menu_view import MenuView, OnlineGameClient
from client.menu import Menu, LobbyManager
from client.constants import *

class BlackjackClient:
    def __init__(self):
        """Inicializar o cliente do jogo"""
        # Inicializar o pygame
        pygame.init()
        pygame.font.init()
        
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Blackjack P2P")
        self.clock = pygame.time.Clock()
        self.running = True
        self.current_view = "menu"
        self.messages = []
        self.player_name = "Player"
        self.name_input_active = False  # Inicialmente não está ativo para permitir ver o menu
        
        # Verificar o saldo do jogador
        try:
            self.player_balance = get_player_balance(self.player_name)
            print(f"Saldo carregado inicialmente: {self.player_balance}")
        except Exception as e:
            print(f"Erro ao carregar saldo: {e}")
            self.player_balance = 1000  # Valor padrão
            
        self.player = None
        self.dealer = None
        self.players = []
        self.current_bet = 0
        self.bet_amount = 100  # Valor inicial da aposta
        self.selected_bot_count = 1
        self.selected_bot_strategy = "random"
        self.cursor_visible = True
        self.cursor_timer = 0
        self.game = None
        self.game_state = None
        self.host_mode = False
        self.show_tutorial = False

        # Fontes - usando try-except para tornar mais robusto
        try:
            self.title_font = pygame.font.SysFont("Arial", 48)
            self.large_font = pygame.font.SysFont("Arial", 36)
            self.medium_font = pygame.font.SysFont("Arial", 24)
            self.small_font = pygame.font.SysFont("Arial", 18)
        except Exception as e:
            print(f"Erro ao carregar fontes: {e}")
            # Usar o font padrão como fallback
            self.title_font = pygame.font.Font(None, 48)
            self.large_font = pygame.font.Font(None, 36)
            self.medium_font = pygame.font.Font(None, 24)
            self.small_font = pygame.font.Font(None, 18)

        # Carregar sprites das cartas com tratamento de erro
        try:
            self.card_sprites = CardSprites()
            if not hasattr(self.card_sprites, 'initialized') or not self.card_sprites.initialized:
                print("CardSprites não inicializado corretamente. Usando fallback.")
                self.card_sprites = None
        except Exception as e:
            print(f"Erro ao carregar sprites das cartas: {e}")
            self.card_sprites = None
        
        # Criar componentes auxiliares - manuseando exceções para cada um
        try:
            self.online_client = OnlineGameClient(self)
        except Exception as e:
            print(f"Erro ao inicializar OnlineGameClient: {e}")
            self.online_client = None
            
        try:
            self.menu = Menu(SCREEN_WIDTH, SCREEN_HEIGHT)
        except Exception as e:
            print(f"Erro ao inicializar Menu: {e}")
            self.menu = None
            
        try:
            self.lobby_manager = LobbyManager(self)
        except Exception as e:
            print(f"Erro ao inicializar LobbyManager: {e}")
            self.lobby_manager = None
            
        try:
            self.menu_view = MenuView(self)
        except Exception as e:
            print(f"Erro ao inicializar MenuView: {e}")
            self.menu_view = None

    def start(self):
        """Iniciar o loop principal do jogo"""
        self.running = True
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

                self.handle_event(event)

            self.update()
            self.render()
            self.clock.tick(60)

        # Salvar o saldo do jogador antes de sair
        if self.player and hasattr(self.player, 'balance'):
            update_player_balance(self.player_name, self.player.balance)
            print(f"Salvando saldo final: {self.player_name} = {self.player.balance}")
            
        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        """Lidar com eventos de entrada do usuário"""
        try:
            if self.current_view == "menu":
                # Delegando para a classe MenuView lidar com eventos do menu
                if self.menu_view and hasattr(self.menu_view, 'handle_event'):
                    if self.menu_view.handle_event(event):
                        return  # Se o evento foi tratado pelo menu_view, não processamos mais
                else:
                    # Fallback para manipulação de eventos de menu se menu_view não estiver disponível
                    self.handle_menu_event_fallback(event)
            elif self.current_view == "bot_selection":
                self.handle_bot_selection_event(event)
            elif self.current_view == "game" and not self.host_mode:  # Modo solo
                self.handle_solo_game_event(event)
            elif self.current_view == "lobby":
                self.handle_lobby_event(event)
            elif self.current_view == "game" and self.host_mode:  # Modo online
                self.handle_game_event(event)
            elif self.current_view == "room_browser" and self.online_client:
                self.online_client.handle_room_browser_event(event)
            elif self.current_view == "create_room" and self.online_client:
                self.online_client.handle_create_room_event(event)
            elif self.current_view == "join_room" and self.online_client:
                self.online_client.handle_join_room_event(event)
        except Exception as e:
            print(f"Erro ao processar evento: {e}")
            
    def handle_menu_event_fallback(self, event):
        """Manipulador de eventos de menu simplificado para fallback"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botão para jogar sozinho
            play_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280, 250, 50)
            if play_rect.collidepoint(mouse_pos):
                self.handle_solo_click()
                
            # Se houver entrada de nome, lidar com isso também
            name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
            if name_input_rect.collidepoint(mouse_pos):
                self.name_input_active = not self.name_input_active
        
        # Manipular teclas para o campo de nome
        if event.type == pygame.KEYDOWN and self.name_input_active:
            if event.key == pygame.K_RETURN:
                self.name_input_active = False
            elif event.key == pygame.K_BACKSPACE:
                self.player_name = self.player_name[:-1]
            else:
                if len(self.player_name) < 20:
                    self.player_name += event.unicode

    def handle_solo_click(self):
        """Manipular clique no botão Jogar Sozinho"""
        # Certifique-se de que o nome não está no modo de edição
        if self.name_input_active:
            self.name_input_active = False
            if not self.player_name:
                self.player_name = "Player"
            self.player_balance = get_player_balance(self.player_name)
        self.current_view = "bot_selection"

    def exit_game(self):
        """Sair do jogo"""
        # Salvar o saldo do jogador antes de sair
        update_player_balance(self.player_name, self.player_balance)
        pygame.quit()
        sys.exit()

    def handle_bot_selection_event(self, event):
        """Lidar com eventos na tela de seleção de bots"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões para selecionar o número de bots
            button_width = 300
            button_height = 60
            button_x = SCREEN_WIDTH // 2 - button_width // 2
            
            # Botão para 1 bot
            bot1_button = pygame.Rect(button_x, 200, button_width, button_height)
            if bot1_button.collidepoint(mouse_pos):
                self.start_single_player(1)
                return
                
            # Botão para 2 bots
            bot2_button = pygame.Rect(button_x, 280, button_width, button_height)
            if bot2_button.collidepoint(mouse_pos):
                self.start_single_player(2)
                return
                
            # Botão para 3 bots
            bot3_button = pygame.Rect(button_x, 360, button_width, button_height)
            if bot3_button.collidepoint(mouse_pos):
                self.start_single_player(3)
                return
                
            # Botão para voltar
            back_button = pygame.Rect(button_x, 460, button_width, button_height)
            if back_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                return

    def start_single_player(self, bot_count):
        """Iniciar jogo no modo solo com bots"""
        try:
            self.selected_bot_count = bot_count
            
            # Criar o jogador humano
            self.player = Player(self.player_name, self.player_balance, str(uuid.uuid4()))
            
            # Criar o jogo
            self.game = Game()
            self.game.initialize_game(self.player)
            
            # Adicionar bots
            for i in range(bot_count):
                bot_difficulty = ["Fácil", "Médio", "Difícil"][i % 3]
                bot_player = Player(f"Bot {bot_difficulty} {i+1}", 1000, f"bot_{i}")
                self.game.add_player(bot_player)
                
            # Iniciar o jogo
            self.game.start_game()
            
            # Atualizar o estado do jogo
            self.game_state = self.game.get_game_state()
            
            # Atualizar a tela para o jogo
            self.current_view = "game"
            self.host_mode = False  # Modo solo
            
            # Limpar mensagens antigas e definir aposta inicial
            self.messages = []
            self.bet_amount = min(100, self.player.balance)
            print(f"Jogo solo iniciado com sucesso com {bot_count} bots")
            
        except Exception as e:
            # Em caso de erro, voltar ao menu e mostrar mensagem
            print(f"Erro ao iniciar jogo solo: {e}")
            self.current_view = "menu"
            self.game = None
            self.game_state = None

    def handle_solo_game_event(self, event):
        """Lidar com eventos no modo de jogo solo"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botão de voltar ao menu
            menu_button = pygame.Rect(10, 10, 120, 40)
            if menu_button.collidepoint(mouse_pos):
                self.current_view = "menu"
                self.game = None
                self.game_state = None
                return
                
            # Altura reservada para controles na parte inferior
            FOOTER_HEIGHT = 150
            footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
            
            # Área de controles
            controls_x = 20
            controls_width = SCREEN_WIDTH // 2 - 40
            button_y = footer_start_y + 45
            
            # Verificar se é vez do jogador
            is_player_turn = (
                self.game_state and
                self.game_state["state"] == "PLAYER_TURN" and
                self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
            )
            
            # Botões de ação no jogo (hit, stand, etc.)
            button_width = 120
            button_spacing = 20
            
            # Botões de ajuste de aposta (apenas na fase de apostas)
            if self.game_state["state"] == "BETTING":
                # Posição do valor da aposta
                bet_amount_x = controls_x + 120
                bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, WHITE)
                
                # Botão de diminuir aposta
                btn_width = 36
                btn_height = 36
                btn_y = footer_start_y + 12
                
                decrease_bet_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
                if decrease_bet_button.collidepoint(mouse_pos):
                    self.decrease_bet()
                    return
                    
                # Botão de aumentar aposta
                increase_bet_button = pygame.Rect(decrease_bet_button.right + 10, btn_y, btn_width, btn_height)
                if increase_bet_button.collidepoint(mouse_pos):
                    self.increase_bet()
                    return
                    
                # Botão de confirmar aposta
                confirm_bet_button = pygame.Rect(controls_x, button_y, button_width, 40)
                if confirm_bet_button.collidepoint(mouse_pos):
                    # Verificar se o jogador tem saldo suficiente
                    if self.player.balance >= self.bet_amount:
                        self.place_bet()
                    else:
                        # Mostrar mensagem de erro
                        self.messages.append("Saldo insuficiente para essa aposta!")
                    return
            
            # Ações durante o turno do jogador
            elif is_player_turn:
                # Botão Hit
                hit_button = pygame.Rect(controls_x, button_y, button_width, 40)
                if hit_button.collidepoint(mouse_pos):
                    self.hit()
                    return
                    
                # Botão Stand
                stand_button = pygame.Rect(controls_x + button_width + button_spacing, button_y, button_width, 40)
                if stand_button.collidepoint(mouse_pos):
                    self.stand()
                    return
            
            # Botão de nova rodada (depois que o jogo termina)
            elif self.game_state["state"] == "GAME_OVER":
                new_round_button = pygame.Rect(controls_x, button_y, button_width * 2 + button_spacing, 40)
                if new_round_button.collidepoint(mouse_pos):
                    self.start_new_round()
                    return
    
    def decrease_bet(self):
        """Diminuir o valor da aposta"""
        if self.bet_amount > 10:  # Mínimo de 10
            self.bet_amount -= 10
            
    def increase_bet(self):
        """Aumentar o valor da aposta"""
        if self.bet_amount < self.player.balance:
            self.bet_amount += 10
            
    def place_bet(self):
        """Confirmar a aposta do jogador"""
        # Colocar a aposta no jogo
        self.game.place_bet(self.player.player_id, self.bet_amount)
        
        # Processar apostas automáticas para os bots
        for player in self.game.state_manager.players:
            if player.player_id != self.player.player_id:
                # Bots apostam um valor aleatório entre 50 e 200
                bot_bet = 50 + (hash(player.player_id) % 4) * 50  # 50, 100, 150 ou 200
                self.game.place_bet(player.player_id, bot_bet)
        
        # Atualizar o estado do jogo
        self.game_state = self.game.get_game_state()
        
    def hit(self):
        """Pedir mais uma carta"""
        if not self.game:
            return
            
        # Pedir carta
        success, message = self.game.hit(self.player.player_id)
        
        if success:
            # Adicionar mensagem
            self.messages.append(message)
        
        # Atualizar o estado do jogo
        self.game_state = self.game.get_game_state()
        
        # Se não for mais a vez do jogador, fazer as jogadas dos bots
        self.process_bot_turns()
            
    def stand(self):
        """Parar de pedir cartas"""
        if not self.game:
            return
            
        # Ficar com as cartas atuais
        success, message = self.game.stand(self.player.player_id)
        
        if success:
            # Adicionar mensagem
            self.messages.append(message)
        
        # Atualizar o estado do jogo
        self.game_state = self.game.get_game_state()
        
        # Processar os turnos dos bots
        self.process_bot_turns()
        
    def process_bot_turns(self):
        """Processar as jogadas dos bots automaticamente"""
        if not self.game or self.game_state["state"] != "PLAYER_TURN":
            return
            
        # Enquanto for o turno de um bot, fazer jogadas automaticamente
        while (self.game_state["state"] == "PLAYER_TURN" and 
               self.game_state["players"][self.game_state["current_player_index"]]["id"] != self.player.player_id):
            
            # Obter o bot atual
            current_bot_index = self.game_state["current_player_index"]
            current_bot = self.game.state_manager.players[current_bot_index]
            
            # Estratégia simples: pedir carta se tiver menos de 17, ficar com 17 ou mais
            hand_value = current_bot.hand.get_value()
            
            # Pausa para dar sensação de que o bot está "pensando"
            time.sleep(0.5)
            
            if hand_value < 16:
                # Bot pede carta
                self.game.hit(current_bot.player_id)
                self.messages.append(f"{current_bot.name} pediu carta.")
            else:
                # Bot fica com as cartas atuais
                self.game.stand(current_bot.player_id)
                self.messages.append(f"{current_bot.name} parou com {hand_value}.")
                
            # Atualizar o estado do jogo
            self.game_state = self.game.get_game_state()
        
    def start_new_round(self):
        """Iniciar uma nova rodada do jogo"""
        if not self.game:
            return
            
        # Atualizar o saldo do jogador antes de continuar
        if self.player:
            self.player_balance = self.player.balance
            update_player_balance(self.player_name, self.player_balance)
        
        # Iniciar nova rodada
        self.game.start_new_round()
        
        # Reiniciar a aposta para o valor padrão
        self.bet_amount = min(100, self.player.balance)
        
        # Atualizar o estado do jogo
        self.game_state = self.game.get_game_state()
        
        # Limpar mensagens antigas
        self.messages = []
        
    def handle_lobby_event(self, event):
        """Lidar com eventos na tela de lobby"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()

            # Botão de iniciar jogo (só para o host)
            if self.host_mode and 100 <= mouse_pos[0] <= 300 and 600 <= mouse_pos[1] <= 650:
                self.lobby_manager.start_game()

            # Botão de voltar
            elif 100 <= mouse_pos[0] <= 300 and 700 <= mouse_pos[1] <= 750:
                self.lobby_manager.leave_lobby()
                
    def handle_game_event(self, event):
        """Lidar com eventos no modo de jogo online"""
        # Código para lidar com eventos do jogo online delegado ao lobby_manager
        pass
        
    def update(self):
        """Atualizar o estado do jogo"""
        # Atualizar o estado do jogo conforme necessário
        pass
        
    def render(self):
        """Renderizar a tela atual"""
        try:
            if self.current_view == "menu":
                if self.menu_view:
                    self.menu_view.render()
                else:
                    # Fallback para o menu se o menu_view não estiver disponível
                    self.screen.fill(GREEN)
                    title = self.title_font.render("Blackjack P2P", True, WHITE)
                    self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
                    pygame.draw.rect(self.screen, LIGHT_BLUE, ((SCREEN_WIDTH - 250) // 2, 280, 250, 50))
                    play_text = self.medium_font.render("Jogar Sozinho", True, BLACK)
                    self.screen.blit(play_text, ((SCREEN_WIDTH - play_text.get_width()) // 2, 295))
            elif self.current_view == "bot_selection":
                self.render_bot_selection()
            elif self.current_view == "game" and not self.host_mode:  # Modo solo
                self.render_solo_game()
            elif self.current_view == "lobby":
                if hasattr(self, 'menu') and self.menu and self.lobby_manager and hasattr(self.lobby_manager, 'room_id'):
                    self.menu.draw_lobby(
                        self.screen,
                        self.lobby_manager.room_id,
                        "Sala de Jogo",
                        self.lobby_manager.player_list,
                        self.lobby_manager.host_mode
                    )
                else:
                    # Fallback para a tela de lobby
                    self.screen.fill(GREEN)
                    text = self.medium_font.render("Sala de Jogo - Erro ao carregar", True, WHITE)
                    self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
            elif self.current_view == "game" and self.host_mode:  # Modo online
                # Apenas um placeholder
                self.screen.fill(GREEN)
                text = self.medium_font.render("Modo Online - Não implementado", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
            elif self.current_view == "room_browser":
                # Apenas um placeholder
                self.screen.fill(GREEN)
                text = self.medium_font.render("Navegando Salas - Não implementado", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
            elif self.current_view == "create_room":
                # Apenas um placeholder
                self.screen.fill(GREEN)
                text = self.medium_font.render("Criando Sala - Não implementado", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
            elif self.current_view == "join_room":
                # Apenas um placeholder
                self.screen.fill(GREEN)
                text = self.medium_font.render("Entrando na Sala - Não implementado", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
            else:
                # Tela padrão caso esteja em um estado desconhecido
                self.screen.fill(GREEN)
                text = self.medium_font.render("Estado desconhecido", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
        except Exception as e:
            # Se ocorrer qualquer erro durante a renderização, mostrar uma tela de erro
            print(f"Erro ao renderizar: {e}")
            self.screen.fill((100, 0, 0))  # Fundo vermelho escuro
            try:
                error_text = self.medium_font.render("Erro de renderização", True, WHITE)
                self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, SCREEN_HEIGHT//2))
            except:
                # Se não conseguir nem mesmo mostrar a mensagem de erro, pelo menos limpe a tela
                pass
        
        # Garantir que a tela seja atualizada
        try:
            pygame.display.flip()
        except Exception as e:
            print(f"Erro ao atualizar display: {e}")
        
    def render_bot_selection(self):
        """Renderizar a tela de seleção de bots"""
        self.screen.fill(GREEN)
        
        # Título com sombra
        title_shadow = self.title_font.render("Selecione o número de bots", True, (0, 40, 0))
        self.screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title_shadow.get_width() // 2 + 2, 52))
        
        title = self.title_font.render("Selecione o número de bots", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        # Adicionar uma descrição
        desc = self.medium_font.render("Escolha contra quantos oponentes você quer jogar", True, LIGHT_GRAY)
        self.screen.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, 110))
        
        # Botões para selecionar o número de bots
        button_width = 300
        button_height = 60
        button_x = SCREEN_WIDTH // 2 - button_width // 2
        
        # Verificar posição do mouse para efeitos de hover
        mouse_pos = pygame.mouse.get_pos()
        
        # Função para desenhar botão com efeitos de hover
        def draw_button(rect, text, icon_text=""):
            is_hover = rect.collidepoint(mouse_pos)
            
            # Desenhar sombra do botão
            shadow_rect = rect.copy()
            shadow_rect.x += 3
            shadow_rect.y += 3
            pygame.draw.rect(self.screen, (0, 60, 0), shadow_rect, border_radius=10)
            
            # Desenhar botão principal
            button_color = (0, 120, 170) if is_hover else (0, 100, 150)  # Azul mais escuro/claro
            pygame.draw.rect(self.screen, button_color, rect, border_radius=10)
            pygame.draw.rect(self.screen, LIGHT_BLUE, rect, 2, border_radius=10)
            
            # Desenhar texto
            text_surface = self.medium_font.render(text, True, WHITE)
            self.screen.blit(text_surface, (rect.centerx - text_surface.get_width() // 2, 
                                           rect.centery - text_surface.get_height() // 2))
            
            # Adicionar ícone se fornecido
            if icon_text:
                icon_surface = self.large_font.render(icon_text, True, YELLOW)
                self.screen.blit(icon_surface, (rect.x + 20, rect.centery - icon_surface.get_height() // 2))
            
            # Adicionar efeito de brilho quando hover
            if is_hover:
                pygame.draw.circle(self.screen, (255, 255, 150), (rect.left - 10, rect.centery), 5)
                pygame.draw.circle(self.screen, (255, 255, 150), (rect.right + 10, rect.centery), 5)
        
        # Botão para 1 bot
        bot1_rect = pygame.Rect(button_x, 200, button_width, button_height)
        draw_button(bot1_rect, "1 Bot", "🤖")
        
        # Botão para 2 bots
        bot2_rect = pygame.Rect(button_x, 280, button_width, button_height)
        draw_button(bot2_rect, "2 Bots", "🤖🤖")
        
        # Botão para 3 bots
        bot3_rect = pygame.Rect(button_x, 360, button_width, button_height)
        draw_button(bot3_rect, "3 Bots", "🤖🤖🤖")
        
        # Botão para voltar
        back_rect = pygame.Rect(button_x, 460, button_width, button_height)
        is_back_hover = back_rect.collidepoint(mouse_pos)
        back_color = (100, 100, 100) if is_back_hover else (80, 80, 80)
        
        # Desenhar sombra para o botão voltar
        back_shadow = back_rect.copy()
        back_shadow.x += 3
        back_shadow.y += 3
        pygame.draw.rect(self.screen, (40, 40, 40), back_shadow, border_radius=10)
        
        # Desenhar o botão voltar
        pygame.draw.rect(self.screen, back_color, back_rect, border_radius=10)
        pygame.draw.rect(self.screen, LIGHT_GRAY, back_rect, 2, border_radius=10)
        
        back_text = self.medium_font.render("Voltar", True, WHITE)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                                    back_rect.centery - back_text.get_height() // 2))
        
        # Adicionar efeito de brilho quando hover no botão voltar
        if is_back_hover:
            pygame.draw.circle(self.screen, (255, 255, 150), (back_rect.left - 10, back_rect.centery), 5)
            pygame.draw.circle(self.screen, (255, 255, 150), (back_rect.right + 10, back_rect.centery), 5)
        
    def render_solo_game(self):
        """Renderizar a tela do jogo solo"""
        # Fundo com gradiente
        for i in range(SCREEN_HEIGHT):
            # Criar um gradiente de verde escuro a verde mais claro
            color = (0, min(80 + i // 10, 120), 0)
            pygame.draw.line(self.screen, color, (0, i), (SCREEN_WIDTH, i))
        
        # Verificar se o jogo está inicializado
        if not self.game or not self.game_state:
            # Exibir mensagem de erro
            error_text = self.medium_font.render("Erro ao inicializar o jogo", True, RED)
            self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, 
                                         SCREEN_HEIGHT//2 - error_text.get_height()//2))
            
            # Botão para voltar ao menu
            back_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 50, 200, 50)
            pygame.draw.rect(self.screen, RED, back_rect, border_radius=10)
            pygame.draw.rect(self.screen, WHITE, back_rect, 2, border_radius=10)
            back_text = self.medium_font.render("Voltar ao Menu", True, WHITE)
            self.screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, 
                                       back_rect.centery - back_text.get_height()//2))
            
            return
            
        # Renderizar o botão de voltar
        back_rect = pygame.Rect(10, 10, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        is_back_hover = back_rect.collidepoint(mouse_pos)
        
        # Sombra do botão
        back_shadow = back_rect.copy()
        back_shadow.x += 2
        back_shadow.y += 2
        pygame.draw.rect(self.screen, (100, 0, 0), back_shadow, border_radius=5)
        
        # Botão principal
        back_color = (200, 50, 50) if is_back_hover else RED
        pygame.draw.rect(self.screen, back_color, back_rect, border_radius=5)
        pygame.draw.rect(self.screen, (255, 150, 150), back_rect, 2, border_radius=5)
        
        # Texto do botão
        back_text = self.small_font.render("Menu", True, WHITE)
        self.screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                                   back_rect.centery - back_text.get_height() // 2))
        
        # Renderizar informações do jogador
        self.render_player_info()
        
        # Renderizar mesa de jogo
        self.render_game_table()
        
        # Renderizar as mãos dos jogadores
        self.render_player_hands()
        
        # Renderizar área de controle
        self.render_game_controls()
        
        # Renderizar mensagens
        self.render_game_messages()
        
    def render_game_table(self):
        """Renderizar a mesa de jogo"""
        # Desenhar mesa redonda
        table_radius = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 3
        table_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)
        
        # Mesa com borda
        pygame.draw.circle(self.screen, DARK_GREEN, table_center, table_radius)
        pygame.draw.circle(self.screen, (0, 150, 0), table_center, table_radius - 3)
        pygame.draw.circle(self.screen, (200, 175, 50), table_center, table_radius - 5, 2)  # borda dourada
        
        # Adicionar um padrão à mesa
        for angle in range(0, 360, 45):
            end_x = table_center[0] + int(math.cos(math.radians(angle)) * (table_radius - 20))
            end_y = table_center[1] + int(math.sin(math.radians(angle)) * (table_radius - 20))
            pygame.draw.line(self.screen, (0, 120, 0), table_center, (end_x, end_y), 1)
        
        # Desenhar um pequeno círculo central
        pygame.draw.circle(self.screen, (0, 100, 0), table_center, 15)
        pygame.draw.circle(self.screen, (200, 175, 50), table_center, 15, 1)
        
    def render_player_info(self):
        """Renderizar informações do jogador"""
        # Criar um painel para as informações
        info_panel_rect = pygame.Rect(SCREEN_WIDTH - 230, 10, 220, 120)
        
        # Desenhar fundo semi-transparente
        s = pygame.Surface((info_panel_rect.width, info_panel_rect.height))
        s.set_alpha(180)
        s.fill((0, 50, 0))
        self.screen.blit(s, info_panel_rect)
        
        # Borda do painel
        pygame.draw.rect(self.screen, (200, 200, 200), info_panel_rect, 2, border_radius=5)
        
        # Nome e saldo do jogador
        player_name_text = self.medium_font.render(self.player_name, True, YELLOW)
        self.screen.blit(player_name_text, (info_panel_rect.x + 10, info_panel_rect.y + 10))
        
        balance_text = self.medium_font.render(f"{self.player.balance} moedas", True, WHITE)
        self.screen.blit(balance_text, (info_panel_rect.x + 10, info_panel_rect.y + 40))
        
        # Estado do jogo
        state_text = self.small_font.render(f"Estado: {self.game_state['state']}", True, LIGHT_GRAY)
        self.screen.blit(state_text, (info_panel_rect.x + 10, info_panel_rect.y + 70))
        
        # Cartas restantes
        cards_text = self.small_font.render(f"Baralho: {self.game_state['cards_remaining']} cartas", True, LIGHT_GRAY)
        self.screen.blit(cards_text, (info_panel_rect.x + 10, info_panel_rect.y + 90))
        
        # Adicionar ícone de cartas
        s = pygame.Surface((30, 40))
        s.fill(BLUE)
        pygame.draw.rect(s, WHITE, (2, 2, 26, 36))
        pygame.draw.rect(s, BLACK, (2, 2, 26, 36), 1)
        self.screen.blit(s, (info_panel_rect.right - 40, info_panel_rect.y + 70))
        
    def render_player_hands(self):
        """Renderizar as mãos dos jogadores"""
        if not self.game_state:
            return
            
        players = self.game_state["players"]
        current_player_index = self.game_state["current_player_index"]
        card_spacing = 30
        
        # Calcular o posicionamento das mãos
        num_players = len(players)
        hand_width = 150  # Largura básica para uma mão
        
        # Distribuir as mãos horizontalmente
        start_x = max(20, (SCREEN_WIDTH - (num_players * hand_width)) // 2)
        
        for i, player in enumerate(players):
            # Destacar o jogador atual
            is_current = i == current_player_index
            is_human = player["id"] == self.player.player_id
            
            # Posição da mão do jogador
            hand_x = start_x + i * hand_width
            hand_y = SCREEN_HEIGHT // 2 - (100 if is_human else 0)
            
            # Fundo para o jogador atual
            if is_current:
                pygame.draw.rect(self.screen, LIGHT_BLUE, (hand_x - 10, hand_y - 10, hand_width, 180), border_radius=5)
            
            # Nome do jogador
            name_color = WHITE if is_human else LIGHT_GRAY
            name_text = self.small_font.render(player["name"], True, name_color)
            self.screen.blit(name_text, (hand_x, hand_y - 25))
            
            # Valor da mão
            value_text = self.small_font.render(f"Valor: {player['hand_value']}", True, WHITE)
            self.screen.blit(value_text, (hand_x, hand_y + 110))
            
            # Status (busted, blackjack, etc.)
            status = ""
            if player["is_busted"]:
                status = "Estourou!"
                status_color = RED
            elif player["hand_value"] == 21:
                status = "Blackjack!"
                status_color = YELLOW
            elif self.game_state["state"] == "GAME_OVER":
                # Verificar se é vencedor
                if player["id"] in [p["id"] for p in self.game_state["players"] if p.get("is_winner", False)]:
                    status = "Vencedor!"
                    status_color = YELLOW
                else:
                    status = "Perdeu"
                    status_color = LIGHT_GRAY
                    
            if status:
                status_text = self.small_font.render(status, True, status_color)
                self.screen.blit(status_text, (hand_x, hand_y + 135))
            
            # Cartas
            cards = player["hand"]
            for j, card in enumerate(cards):
                card_x = hand_x + j * card_spacing
                card_y = hand_y
                
                # Renderizar carta
                if self.card_sprites:
                    try:
                        self.card_sprites.draw_card(self.screen, card["suit"], card["value"], card_x, card_y)
                    except Exception as e:
                        # Fallback: desenhar uma carta simples em caso de erro
                        pygame.draw.rect(self.screen, WHITE, (card_x, card_y, 50, 70), border_radius=3)
                        pygame.draw.rect(self.screen, BLACK, (card_x, card_y, 50, 70), 2, border_radius=3)
                        
                        # Desenhar valor da carta
                        value_str = str(card["value"])
                        value_text = self.small_font.render(value_str, True, BLACK)
                        self.screen.blit(value_text, (card_x + 25 - value_text.get_width()//2, 
                                                    card_y + 35 - value_text.get_height()//2))
                else:
                    # Fallback: desenhar uma carta simples
                    pygame.draw.rect(self.screen, WHITE, (card_x, card_y, 50, 70), border_radius=3)
                    pygame.draw.rect(self.screen, BLACK, (card_x, card_y, 50, 70), 2, border_radius=3)
                    
                    # Desenhar valor da carta
                    value_str = str(card["value"])
                    value_text = self.small_font.render(value_str, True, BLACK)
                    self.screen.blit(value_text, (card_x + 25 - value_text.get_width()//2, 
                                                card_y + 35 - value_text.get_height()//2))
            
    def render_game_controls(self):
        """Renderizar os controles do jogo"""
        # Área de controles na parte inferior
        FOOTER_HEIGHT = 150
        footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
        
        pygame.draw.rect(self.screen, DARK_GREEN, (0, footer_start_y, SCREEN_WIDTH, FOOTER_HEIGHT))
        
        # Área de controles
        controls_x = 20
        controls_width = SCREEN_WIDTH // 2 - 40
        button_y = footer_start_y + 45
        
        # Verificar se é vez do jogador
        is_player_turn = (
            self.game_state and
            self.game_state["state"] == "PLAYER_TURN" and
            self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
        )
        
        # Controles específicos para cada fase do jogo
        if self.game_state["state"] == "BETTING":
            # Fase de apostas
            pygame.draw.rect(self.screen, LIGHT_GRAY, (controls_x, footer_start_y + 10, controls_width, 30))
            bet_text = self.medium_font.render("Aposta:", True, BLACK)
            self.screen.blit(bet_text, (controls_x + 10, footer_start_y + 15))
            
            # Valor da aposta
            bet_amount_x = controls_x + 120
            bet_amount_text = self.medium_font.render(f"{self.bet_amount}", True, WHITE)
            self.screen.blit(bet_amount_text, (bet_amount_x, footer_start_y + 15))
            
            # Botões de ajuste da aposta
            btn_width = 36
            btn_height = 36
            btn_y = footer_start_y + 12
            
            # Botão -
            pygame.draw.rect(self.screen, LIGHT_GRAY, (bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height))
            minus_text = self.medium_font.render("-", True, BLACK)
            self.screen.blit(minus_text, (bet_amount_x + bet_amount_text.get_width() + 15 + btn_width // 2 - minus_text.get_width() // 2, btn_y + btn_height // 2 - minus_text.get_height() // 2))
            
            # Botão +
            pygame.draw.rect(self.screen, LIGHT_GRAY, (bet_amount_x + bet_amount_text.get_width() + 15 + btn_width + 10, btn_y, btn_width, btn_height))
            plus_text = self.medium_font.render("+", True, BLACK)
            self.screen.blit(plus_text, (bet_amount_x + bet_amount_text.get_width() + 15 + btn_width + 10 + btn_width // 2 - plus_text.get_width() // 2, btn_y + btn_height // 2 - plus_text.get_height() // 2))
            
            # Botão de confirmar aposta
            pygame.draw.rect(self.screen, BLUE, (controls_x, button_y, 120, 40))
            confirm_text = self.medium_font.render("Apostar", True, WHITE)
            self.screen.blit(confirm_text, (controls_x + 60 - confirm_text.get_width() // 2, button_y + 20 - confirm_text.get_height() // 2))
            
        elif is_player_turn:
            # Turno do jogador - botões de ação
            button_width = 120
            button_spacing = 20
            
            # Botão Hit
            pygame.draw.rect(self.screen, RED, (controls_x, button_y, button_width, 40))
            hit_text = self.medium_font.render("Hit", True, WHITE)
            self.screen.blit(hit_text, (controls_x + button_width // 2 - hit_text.get_width() // 2, button_y + 20 - hit_text.get_height() // 2))
            
            # Botão Stand
            pygame.draw.rect(self.screen, BLUE, (controls_x + button_width + button_spacing, button_y, button_width, 40))
            stand_text = self.medium_font.render("Stand", True, WHITE)
            self.screen.blit(stand_text, (controls_x + button_width + button_spacing + button_width // 2 - stand_text.get_width() // 2, button_y + 20 - stand_text.get_height() // 2))
            
        elif self.game_state["state"] == "GAME_OVER":
            # Jogo terminado - botão de nova rodada
            pygame.draw.rect(self.screen, GREEN, (controls_x, button_y, 260, 40))
            new_round_text = self.medium_font.render("Nova Rodada", True, WHITE)
            self.screen.blit(new_round_text, (controls_x + 130 - new_round_text.get_width() // 2, button_y + 20 - new_round_text.get_height() // 2))
            
        else:
            # Fase de espera - mostrar mensagem
            waiting_text = self.medium_font.render("Aguarde sua vez...", True, WHITE)
            self.screen.blit(waiting_text, (controls_x, button_y + 5))
            
    def render_game_messages(self):
        """Renderizar mensagens do jogo"""
        # Área de mensagens na parte inferior direita
        messages_x = SCREEN_WIDTH // 2 + 20
        messages_width = SCREEN_WIDTH // 2 - 40
        messages_y = SCREEN_HEIGHT - 150
        
        pygame.draw.rect(self.screen, DARK_GREEN, (messages_x - 10, messages_y, messages_width + 20, 140))
        
        # Título da área de mensagens
        msg_title = self.small_font.render("Mensagens", True, WHITE)
        self.screen.blit(msg_title, (messages_x, messages_y + 5))
        
        # Mostrar apenas as últimas 4 mensagens para não sobrecarregar a tela
        y_offset = 30
        for i in range(min(4, len(self.messages))):
            msg = self.messages[-i-1]  # Começar da mensagem mais recente
            msg_text = self.small_font.render(msg, True, LIGHT_GRAY)
            
            # Limitar o tamanho da mensagem para caber na área
            if msg_text.get_width() > messages_width:
                # Truncar a mensagem e adicionar "..."
                truncated = False
                while msg_text.get_width() > messages_width:
                    msg = msg[:-1]
                    msg_text = self.small_font.render(msg + "...", True, LIGHT_GRAY)
                    truncated = True
                
                if truncated:
                    msg += "..."
                    msg_text = self.small_font.render(msg, True, LIGHT_GRAY)
            
            self.screen.blit(msg_text, (messages_x, messages_y + y_offset))
            y_offset += 25
            
    # Métodos para delegação à interfaces de outros componentes
    def render_lobby(self):
        """Renderizar a tela de lobby"""
        # Delegar para o menu.py
        self.menu.draw_lobby(
            self.screen,
            self.lobby_manager.room_id,
            "Sala de Jogo",
            self.lobby_manager.player_list,
            self.lobby_manager.host_mode
        )
        
    def render_online_game(self):
        """Renderizar a tela do jogo online"""
        # Lógica para renderizar o jogo online, delegada ao lobby_manager
        pass
        
    def render_room_browser(self):
        """Renderizar a tela de navegação de salas"""
        # Lógica para renderizar a navegação de salas
        pass
        
    def render_create_room(self):
        """Renderizar a tela de criação de sala"""
        # Lógica para renderizar a criação de sala
        pass
        
    def render_join_room(self):
        """Renderizar a tela de entrada em sala"""
        # Lógica para renderizar a entrada em sala
        pass

if __name__ == '__main__':
    client = BlackjackClient()
    client.start()

