import pygame
import math
import time
from client.constants import *

class UIManager:
    def __init__(self, client):
        """Inicializar o gerenciador de interface"""
        self.client = client
        
        # Inicializar fontes - usando try-except para tornar mais robusto
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
        
    def render_bot_selection(self, screen, selected_bot_count):
        """Renderizar a tela de seleção de bots"""
        screen.fill(GREEN)
        
        # Título com sombra
        title_shadow = self.title_font.render("Selecione o número de bots", True, (0, 40, 0))
        screen.blit(title_shadow, (SCREEN_WIDTH // 2 - title_shadow.get_width() // 2 + 2, 52))
        
        title = self.title_font.render("Selecione o número de bots", True, WHITE)
        screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 50))
        
        # Adicionar uma descrição
        desc = self.medium_font.render("Escolha contra quantos oponentes você quer jogar", True, LIGHT_GRAY)
        screen.blit(desc, (SCREEN_WIDTH // 2 - desc.get_width() // 2, 110))
        
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
            pygame.draw.rect(screen, (0, 60, 0), shadow_rect, border_radius=10)
            
            # Desenhar botão principal
            button_color = (0, 120, 170) if is_hover else (0, 100, 150)  # Azul mais escuro/claro
            pygame.draw.rect(screen, button_color, rect, border_radius=10)
            pygame.draw.rect(screen, LIGHT_BLUE, rect, 2, border_radius=10)
            
            # Desenhar texto
            text_surface = self.medium_font.render(text, True, WHITE)
            screen.blit(text_surface, (rect.centerx - text_surface.get_width() // 2, 
                                        rect.centery - text_surface.get_height() // 2))
            
            # Adicionar ícone se fornecido
            if icon_text:
                icon_surface = self.large_font.render(icon_text, True, YELLOW)
                screen.blit(icon_surface, (rect.x + 20, rect.centery - icon_surface.get_height() // 2))
            
            # Adicionar efeito de brilho quando hover
            if is_hover:
                pygame.draw.circle(screen, (255, 255, 150), (rect.left - 10, rect.centery), 5)
                pygame.draw.circle(screen, (255, 255, 150), (rect.right + 10, rect.centery), 5)
        
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
        pygame.draw.rect(screen, (40, 40, 40), back_shadow, border_radius=10)
        
        # Desenhar o botão voltar
        pygame.draw.rect(screen, back_color, back_rect, border_radius=10)
        pygame.draw.rect(screen, LIGHT_GRAY, back_rect, 2, border_radius=10)
        
        back_text = self.medium_font.render("Voltar", True, WHITE)
        screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                                back_rect.centery - back_text.get_height() // 2))
        
        # Adicionar efeito de brilho quando hover no botão voltar
        if is_back_hover:
            pygame.draw.circle(screen, (255, 255, 150), (back_rect.left - 10, back_rect.centery), 5)
            pygame.draw.circle(screen, (255, 255, 150), (back_rect.right + 10, back_rect.centery), 5)
            
        return bot1_rect, bot2_rect, bot3_rect, back_rect
        
    def render_solo_game(self, screen, game, game_state, player, player_name, player_balance, 
                        bet_amount, card_sprites, messages):
        """Renderizar a tela do jogo solo"""
        # Fundo com gradiente
        for i in range(SCREEN_HEIGHT):
            # Criar um gradiente de verde escuro a verde mais claro
            color = (0, min(80 + i // 10, 120), 0)
            pygame.draw.line(screen, color, (0, i), (SCREEN_WIDTH, i))
        
        # Verificar se o jogo está inicializado
        if not game or not game_state:
            # Exibir mensagem de erro
            error_text = self.medium_font.render("Erro ao inicializar o jogo", True, RED)
            screen.blit(error_text, (SCREEN_WIDTH//2 - error_text.get_width()//2, 
                                     SCREEN_HEIGHT//2 - error_text.get_height()//2))
            
            # Botão para voltar ao menu
            back_rect = pygame.Rect(SCREEN_WIDTH//2 - 100, SCREEN_HEIGHT//2 + 50, 200, 50)
            pygame.draw.rect(screen, RED, back_rect, border_radius=10)
            pygame.draw.rect(screen, WHITE, back_rect, 2, border_radius=10)
            back_text = self.medium_font.render("Voltar ao Menu", True, WHITE)
            screen.blit(back_text, (back_rect.centerx - back_text.get_width()//2, 
                                   back_rect.centery - back_text.get_height()//2))
            
            return back_rect, None, None, None, None
            
        # Renderizar o botão de voltar
        back_rect = pygame.Rect(10, 10, 120, 40)
        mouse_pos = pygame.mouse.get_pos()
        is_back_hover = back_rect.collidepoint(mouse_pos)
        
        # Sombra do botão
        back_shadow = back_rect.copy()
        back_shadow.x += 2
        back_shadow.y += 2
        pygame.draw.rect(screen, (100, 0, 0), back_shadow, border_radius=5)
        
        # Botão principal
        back_color = (200, 50, 50) if is_back_hover else RED
        pygame.draw.rect(screen, back_color, back_rect, border_radius=5)
        pygame.draw.rect(screen, (255, 150, 150), back_rect, 2, border_radius=5)
        
        # Texto do botão
        back_text = self.small_font.render("Menu", True, WHITE)
        screen.blit(back_text, (back_rect.centerx - back_text.get_width() // 2, 
                               back_rect.centery - back_text.get_height() // 2))
        
        # Renderizar informações do jogador
        self.render_player_info(screen, player_name, player, game_state)
        
        # Renderizar mesa de jogo
        self.render_game_table(screen)
        
        # Renderizar as mãos dos jogadores
        self.render_player_hands(screen, game_state, player, card_sprites)
        
        # Renderizar área de controle
        betting_buttons, game_buttons = self.render_game_controls(screen, game_state, player, bet_amount)
        
        # Renderizar mensagens
        self.render_game_messages(screen, messages)
        
        return back_rect, betting_buttons, game_buttons, None, None
        
    def render_game_table(self, screen):
        """Renderizar a mesa de jogo"""
        # Desenhar mesa redonda
        table_radius = min(SCREEN_WIDTH, SCREEN_HEIGHT) // 3
        table_center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30)
        
        # Mesa com borda
        pygame.draw.circle(screen, DARK_GREEN, table_center, table_radius)
        pygame.draw.circle(screen, (0, 150, 0), table_center, table_radius - 3)
        pygame.draw.circle(screen, (200, 175, 50), table_center, table_radius - 5, 2)  # borda dourada
        
        # Adicionar um padrão à mesa
        for angle in range(0, 360, 45):
            end_x = table_center[0] + int(math.cos(math.radians(angle)) * (table_radius - 20))
            end_y = table_center[1] + int(math.sin(math.radians(angle)) * (table_radius - 20))
            pygame.draw.line(screen, (0, 120, 0), table_center, (end_x, end_y), 1)
        
        # Desenhar um pequeno círculo central
        pygame.draw.circle(screen, (0, 100, 0), table_center, 15)
        pygame.draw.circle(screen, (200, 175, 50), table_center, 15, 1)
        
    def render_player_info(self, screen, player_name, player, game_state):
        """Renderizar informações do jogador"""
        # Criar um painel para as informações
        info_panel_rect = pygame.Rect(SCREEN_WIDTH - 230, 10, 220, 120)
        
        # Desenhar fundo semi-transparente
        s = pygame.Surface((info_panel_rect.width, info_panel_rect.height))
        s.set_alpha(180)
        s.fill((0, 50, 0))
        screen.blit(s, info_panel_rect)
        
        # Borda do painel
        pygame.draw.rect(screen, (200, 200, 200), info_panel_rect, 2, border_radius=5)
        
        # Nome e saldo do jogador
        player_name_text = self.medium_font.render(player_name, True, YELLOW)
        screen.blit(player_name_text, (info_panel_rect.x + 10, info_panel_rect.y + 10))
        
        balance_text = self.medium_font.render(f"{player.balance} moedas", True, WHITE)
        screen.blit(balance_text, (info_panel_rect.x + 10, info_panel_rect.y + 40))
        
        # Estado do jogo
        state_text = self.small_font.render(f"Estado: {game_state['state']}", True, LIGHT_GRAY)
        screen.blit(state_text, (info_panel_rect.x + 10, info_panel_rect.y + 70))
        
        # Cartas restantes
        cards_text = self.small_font.render(f"Baralho: {game_state['cards_remaining']} cartas", True, LIGHT_GRAY)
        screen.blit(cards_text, (info_panel_rect.x + 10, info_panel_rect.y + 90))
        
        # Adicionar ícone de cartas
        s = pygame.Surface((30, 40))
        s.fill(BLUE)
        pygame.draw.rect(s, WHITE, (2, 2, 26, 36))
        pygame.draw.rect(s, BLACK, (2, 2, 26, 36), 1)
        screen.blit(s, (info_panel_rect.right - 40, info_panel_rect.y + 70))
        
    def render_player_hands(self, screen, game_state, player, card_sprites):
        """Renderizar as mãos dos jogadores"""
        if not game_state:
            return
            
        players = game_state["players"]
        current_player_index = game_state["current_player_index"]
        card_spacing = 30
        
        # Calcular o posicionamento das mãos
        num_players = len(players)
        hand_width = 150  # Largura básica para uma mão
        
        # Distribuir as mãos horizontalmente
        start_x = max(20, (SCREEN_WIDTH - (num_players * hand_width)) // 2)
        
        for i, player_data in enumerate(players):
            # Destacar o jogador atual
            is_current = i == current_player_index
            is_human = player_data["id"] == player.player_id
            
            # Posição da mão do jogador
            hand_x = start_x + i * hand_width
            hand_y = SCREEN_HEIGHT // 2 - (100 if is_human else 0)
            
            # Fundo para o jogador atual
            if is_current:
                pygame.draw.rect(screen, LIGHT_BLUE, (hand_x - 10, hand_y - 10, hand_width, 180), border_radius=5)
            
            # Nome do jogador
            name_color = WHITE if is_human else LIGHT_GRAY
            name_text = self.small_font.render(player_data["name"], True, name_color)
            screen.blit(name_text, (hand_x, hand_y - 25))
            
            # Valor da mão
            value_text = self.small_font.render(f"Valor: {player_data['hand_value']}", True, WHITE)
            screen.blit(value_text, (hand_x, hand_y + 110))
            
            # Status (busted, blackjack, etc.)
            status = ""
            if player_data["is_busted"]:
                status = "Estourou!"
                status_color = RED
            elif player_data["hand_value"] == 21:
                status = "Blackjack!"
                status_color = YELLOW
            elif game_state["state"] == "GAME_OVER":
                # Verificar se é vencedor
                if player_data["id"] in [p["id"] for p in game_state["players"] if p.get("is_winner", False)]:
                    status = "Vencedor!"
                    status_color = YELLOW
                else:
                    status = "Perdeu"
                    status_color = LIGHT_GRAY
                    
            if status:
                status_text = self.small_font.render(status, True, status_color)
                screen.blit(status_text, (hand_x, hand_y + 135))
            
            # Cartas
            cards = player_data["hand"]
            for j, card in enumerate(cards):
                card_x = hand_x + j * card_spacing
                card_y = hand_y
                
                # Renderizar carta
                if card_sprites:
                    try:
                        card_sprites.draw_card(screen, card["suit"], card["value"], card_x, card_y)
                    except Exception as e:
                        # Fallback: desenhar uma carta simples em caso de erro
                        pygame.draw.rect(screen, WHITE, (card_x, card_y, 50, 70), border_radius=3)
                        pygame.draw.rect(screen, BLACK, (card_x, card_y, 50, 70), 2, border_radius=3)
                        
                        # Desenhar valor da carta
                        value_str = str(card["value"])
                        value_text = self.small_font.render(value_str, True, BLACK)
                        screen.blit(value_text, (card_x + 25 - value_text.get_width()//2, 
                                                card_y + 35 - value_text.get_height()//2))
                else:
                    # Fallback: desenhar uma carta simples
                    pygame.draw.rect(screen, WHITE, (card_x, card_y, 50, 70), border_radius=3)
                    pygame.draw.rect(screen, BLACK, (card_x, card_y, 50, 70), 2, border_radius=3)
                    
                    # Desenhar valor da carta
                    value_str = str(card["value"])
                    value_text = self.small_font.render(value_str, True, BLACK)
                    screen.blit(value_text, (card_x + 25 - value_text.get_width()//2, 
                                            card_y + 35 - value_text.get_height()//2))
            
    def render_game_controls(self, screen, game_state, player, bet_amount):
        """Renderizar os controles do jogo"""
        # Área de controles na parte inferior
        FOOTER_HEIGHT = 150
        footer_start_y = SCREEN_HEIGHT - FOOTER_HEIGHT
        
        pygame.draw.rect(screen, DARK_GREEN, (0, footer_start_y, SCREEN_WIDTH, FOOTER_HEIGHT))
        
        # Área de controles
        controls_x = 20
        controls_width = SCREEN_WIDTH // 2 - 40
        button_y = footer_start_y + 45
        
        betting_buttons = []
        game_buttons = []
        
        # Verificar se é vez do jogador
        is_player_turn = (
            game_state and
            game_state["state"] == "PLAYER_TURN" and
            game_state["players"][game_state["current_player_index"]]["id"] == player.player_id
        )
        
        # Controles específicos para cada fase do jogo
        if game_state["state"] == "BETTING":
            # Fase de apostas
            pygame.draw.rect(screen, LIGHT_GRAY, (controls_x, footer_start_y + 10, controls_width, 30))
            bet_text = self.medium_font.render("Aposta:", True, BLACK)
            screen.blit(bet_text, (controls_x + 10, footer_start_y + 15))
            
            # Valor da aposta
            bet_amount_x = controls_x + 120
            bet_amount_text = self.medium_font.render(f"{bet_amount}", True, WHITE)
            screen.blit(bet_amount_text, (bet_amount_x, footer_start_y + 15))
            
            # Botões de ajuste da aposta
            btn_width = 36
            btn_height = 36
            btn_y = footer_start_y + 12
            
            # Botão -
            minus_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15, btn_y, btn_width, btn_height)
            pygame.draw.rect(screen, LIGHT_GRAY, minus_button)
            minus_text = self.medium_font.render("-", True, BLACK)
            screen.blit(minus_text, (minus_button.centerx - minus_text.get_width() // 2, 
                                    minus_button.centery - minus_text.get_height() // 2))
            
            # Botão +
            plus_button = pygame.Rect(bet_amount_x + bet_amount_text.get_width() + 15 + btn_width + 10, btn_y, btn_width, btn_height)
            pygame.draw.rect(screen, LIGHT_GRAY, plus_button)
            plus_text = self.medium_font.render("+", True, BLACK)
            screen.blit(plus_text, (plus_button.centerx - plus_text.get_width() // 2, 
                                   plus_button.centery - plus_text.get_height() // 2))
            
            # Botão de confirmar aposta
            confirm_button = pygame.Rect(controls_x, button_y, 120, 40)
            pygame.draw.rect(screen, BLUE, confirm_button)
            confirm_text = self.medium_font.render("Apostar", True, WHITE)
            screen.blit(confirm_text, (confirm_button.centerx - confirm_text.get_width() // 2, 
                                      confirm_button.centery - confirm_text.get_height() // 2))
            
            betting_buttons = [minus_button, plus_button, confirm_button]
            
        elif is_player_turn:
            # Turno do jogador - botões de ação
            button_width = 120
            button_spacing = 20
            
            # Botão Hit
            hit_button = pygame.Rect(controls_x, button_y, button_width, 40)
            pygame.draw.rect(screen, RED, hit_button)
            hit_text = self.medium_font.render("Hit", True, WHITE)
            screen.blit(hit_text, (hit_button.centerx - hit_text.get_width() // 2, 
                                  hit_button.centery - hit_text.get_height() // 2))
            
            # Botão Stand
            stand_button = pygame.Rect(controls_x + button_width + button_spacing, button_y, button_width, 40)
            pygame.draw.rect(screen, BLUE, stand_button)
            stand_text = self.medium_font.render("Stand", True, WHITE)
            screen.blit(stand_text, (stand_button.centerx - stand_text.get_width() // 2, 
                                    stand_button.centery - stand_text.get_height() // 2))
            
            game_buttons = [hit_button, stand_button]
            
        elif game_state["state"] == "GAME_OVER":
            # Jogo terminado - botão de nova rodada
            new_round_button = pygame.Rect(controls_x, button_y, 260, 40)
            pygame.draw.rect(screen, GREEN, new_round_button)
            new_round_text = self.medium_font.render("Nova Rodada", True, WHITE)
            screen.blit(new_round_text, (new_round_button.centerx - new_round_text.get_width() // 2, 
                                        new_round_button.centery - new_round_text.get_height() // 2))
            
            game_buttons = [new_round_button]
            
        else:
            # Fase de espera - mostrar mensagem
            waiting_text = self.medium_font.render("Aguarde sua vez...", True, WHITE)
            screen.blit(waiting_text, (controls_x, button_y + 5))
            
        return betting_buttons, game_buttons
            
    def render_game_messages(self, screen, messages):
        """Renderizar mensagens do jogo"""
        # Área de mensagens na parte inferior direita
        messages_x = SCREEN_WIDTH // 2 + 20
        messages_width = SCREEN_WIDTH // 2 - 40
        messages_y = SCREEN_HEIGHT - 150
        
        pygame.draw.rect(screen, DARK_GREEN, (messages_x - 10, messages_y, messages_width + 20, 140))
        
        # Título da área de mensagens
        msg_title = self.small_font.render("Mensagens", True, WHITE)
        screen.blit(msg_title, (messages_x, messages_y + 5))
        
        # Mostrar apenas as últimas 4 mensagens para não sobrecarregar a tela
        y_offset = 30
        for i in range(min(4, len(messages))):
            msg = messages[-i-1]  # Começar da mensagem mais recente
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
            
            screen.blit(msg_text, (messages_x, messages_y + y_offset))
            y_offset += 25

    def handle_menu_event_fallback(self, event, screen, player_name, player_balance):
        """Manipulador de eventos de menu simplificado para fallback"""
        result = None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botão para jogar sozinho
            play_rect = pygame.Rect((SCREEN_WIDTH - 250) // 2, 280, 250, 50)
            if play_rect.collidepoint(mouse_pos):
                result = "solo"
                
            # Se houver entrada de nome, lidar com isso também
            name_input_rect = pygame.Rect(SCREEN_WIDTH // 2 - 90, 150, 180, 30)
            if name_input_rect.collidepoint(mouse_pos):
                result = "name_input"
        
        return result 