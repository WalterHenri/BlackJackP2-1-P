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
from client.menu_view import MenuView
from client.ui_manager import UIManager
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
        
        # Criar gerenciador de interface
        self.ui_manager = UIManager(self)
        
        # Criar componentes auxiliares - manuseando exceções para cada um
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
                    result = self.ui_manager.handle_menu_event_fallback(event, self.screen, self.player_name, self.player_balance)
                    if result == "solo":
                        self.handle_solo_click()
                    elif result == "name_input":
                        self.name_input_active = not self.name_input_active
            elif self.current_view == "bot_selection":
                self.handle_bot_selection_event(event)
            elif self.current_view == "game" and not self.host_mode:  # Modo solo
                self.handle_solo_game_event(event)
        except Exception as e:
            print(f"Erro ao processar evento: {e}")

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
            # Obter as áreas dos botões do UI Manager
            bot1_rect, bot2_rect, bot3_rect, back_rect = self.ui_manager.render_bot_selection(self.screen, self.selected_bot_count)
            mouse_pos = pygame.mouse.get_pos()
            
            # Verificar cliques nos botões
            if bot1_rect.collidepoint(mouse_pos):
                self.start_single_player(1)
                return
            elif bot2_rect.collidepoint(mouse_pos):
                self.start_single_player(2)
                return
            elif bot3_rect.collidepoint(mouse_pos):
                self.start_single_player(3)
                return
            elif back_rect.collidepoint(mouse_pos):
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
            # Obter as áreas dos botões do UI Manager
            back_rect, betting_buttons, game_buttons, _, _ = self.ui_manager.render_solo_game(
                self.screen, self.game, self.game_state, self.player, 
                self.player_name, self.player_balance, self.bet_amount, 
                self.card_sprites, self.messages
            )
            
            mouse_pos = pygame.mouse.get_pos()
            
            # Verificar clique no botão de voltar
            if back_rect.collidepoint(mouse_pos):
                self.current_view = "menu"
                self.game = None
                self.game_state = None
                return
            
            # Verificar fase de apostas
            if self.game_state["state"] == "BETTING" and betting_buttons:
                # Botão de diminuir aposta
                if betting_buttons[0].collidepoint(mouse_pos):
                    self.decrease_bet()
                    return
                    
                # Botão de aumentar aposta
                if betting_buttons[1].collidepoint(mouse_pos):
                    self.increase_bet()
                    return
                    
                # Botão de confirmar aposta
                if betting_buttons[2].collidepoint(mouse_pos):
                    # Verificar se o jogador tem saldo suficiente
                    if self.player.balance >= self.bet_amount:
                        self.place_bet()
                    else:
                        # Mostrar mensagem de erro
                        self.messages.append("Saldo insuficiente para essa aposta!")
                    return
            
            # Verificar se é vez do jogador
            is_player_turn = (
                self.game_state and
                self.game_state["state"] == "PLAYER_TURN" and
                self.game_state["players"][self.game_state["current_player_index"]]["id"] == self.player.player_id
            )
            
            # Ações durante o turno do jogador
            if is_player_turn and game_buttons and len(game_buttons) >= 2:
                # Botão Hit
                if game_buttons[0].collidepoint(mouse_pos):
                    self.hit()
                    return
                    
                # Botão Stand
                if game_buttons[1].collidepoint(mouse_pos):
                    self.stand()
                    return
            
            # Botão de nova rodada (depois que o jogo termina)
            if self.game_state["state"] == "GAME_OVER" and game_buttons:
                if game_buttons[0].collidepoint(mouse_pos):
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
                    title = self.ui_manager.title_font.render("Blackjack P2P", True, WHITE)
                    self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
                    pygame.draw.rect(self.screen, LIGHT_BLUE, ((SCREEN_WIDTH - 250) // 2, 280, 250, 50))
                    play_text = self.ui_manager.medium_font.render("Jogar Sozinho", True, BLACK)
                    self.screen.blit(play_text, ((SCREEN_WIDTH - play_text.get_width()) // 2, 295))
            elif self.current_view == "bot_selection":
                self.ui_manager.render_bot_selection(self.screen, self.selected_bot_count)
            elif self.current_view == "game" and not self.host_mode:  # Modo solo
                self.ui_manager.render_solo_game(
                    self.screen, self.game, self.game_state, self.player,
                    self.player_name, self.player_balance, self.bet_amount,
                    self.card_sprites, self.messages
                )
            else:
                # Tela padrão caso esteja em um estado desconhecido
                self.screen.fill(GREEN)
                text = self.ui_manager.medium_font.render("Estado desconhecido", True, WHITE)
                self.screen.blit(text, (SCREEN_WIDTH//2 - text.get_width()//2, SCREEN_HEIGHT//2))
        except Exception as e:
            # Se ocorrer qualquer erro durante a renderização, mostrar uma tela de erro
            print(f"Erro ao renderizar: {e}")
            self.screen.fill((100, 0, 0))  # Fundo vermelho escuro
            try:
                error_text = self.ui_manager.medium_font.render("Erro de renderização", True, WHITE)
                self.screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, SCREEN_HEIGHT//2))
            except:
                # Se não conseguir nem mesmo mostrar a mensagem de erro, pelo menos limpe a tela
                pass
        
        # Garantir que a tela seja atualizada
        try:
            pygame.display.flip()
        except Exception as e:
            print(f"Erro ao atualizar display: {e}")

if __name__ == '__main__':
    client = BlackjackClient()
    client.start()

