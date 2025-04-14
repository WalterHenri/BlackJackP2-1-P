import pygame
import socket
from constants import *
from cards import SpriteSheet

class GameRenderer:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        
        # Estado do jogo
        self.game_state = "PLAYING"
        self.game_over = False
        
        # Carrega a imagem de fundo
        self.background_image = pygame.image.load("assets/capa2.png")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Carrega a fonte personalizada
        self.custom_font = pygame.font.Font("assets/font-jersey.ttf", 30)
        self.small_custom_font = pygame.font.Font("assets/font-jersey.ttf", 20)
        self.title_font = pygame.font.Font("assets/font-jersey.ttf", 40)
        
        # Carrega o sprite sheet das cartas
        self.card_sprites = SpriteSheet("assets/cards.png")
        
        # Escala para as cartas (ajustar conforme necessário)
        self.card_scale = 0.5  # 50% do tamanho original
        
        # Botões maiores para gameplay
        button_width = 180
        button_height = 60
        button_y = SCREEN_HEIGHT - 80
        
        self.hit_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width - 30,  # 30px de espaço entre os botões
            button_y,
            button_width,
            button_height
        )
        
        self.stand_button = pygame.Rect(
            SCREEN_WIDTH // 2 + 30,  # 30px de espaço entre os botões
            button_y,
            button_width,
            button_height
        )
    
    def draw_card(self, card, position):
        # Obtém a sprite da carta correspondente
        sprite = self.card_sprites.get_sprite(card.suit, card.value)
        
        if sprite:
            # Calcula o novo tamanho da carta
            scaled_width = int(self.card_sprites.card_width * self.card_scale)
            scaled_height = int(self.card_sprites.card_height * self.card_scale)
            
            # Redimensiona a sprite
            scaled_sprite = pygame.transform.scale(sprite, (scaled_width, scaled_height))
            
            # Desenha a carta
            self.screen.blit(scaled_sprite, position)
        else:
            # Fallback para desenho manual se a sprite não for encontrada
            rect = pygame.Rect(position[0], position[1], CARD_WIDTH, CARD_HEIGHT)
            pygame.draw.rect(self.screen, WHITE, rect)
            pygame.draw.rect(self.screen, BLACK, rect, 2)
            
            color = RED if card.suit in ['Hearts', 'Diamonds'] else BLACK
            card_text = self.font.render(f"{card.value}", True, color)
            suit_text = self.font.render(card.suit[0], True, color)
            
            self.screen.blit(card_text, (position[0] + 10, position[1] + 10))
            self.screen.blit(suit_text, (position[0] + 10, position[1] + 40))
    
    def draw_hand(self, player, is_local):
        # Posicionamento vertical melhorado com maior distanciamento
        y_pos = SCREEN_HEIGHT - 280 if is_local else 80
        label = "Sua mão:" if is_local else "Oponente:"
        score_text = f"Pontuação: {player.score}"
        status_map = {"playing": "Jogando", "standing": "Parou", "busted": "Estourou"}
        status_text = f"Status: {status_map.get(player.status, player.status)}"
        
        # Adiciona um fundo semitransparente para melhorar a visibilidade
        # Ocupando quase toda a largura da tela com pequenas margens
        margin = 20
        info_bg_rect = pygame.Rect(margin, y_pos - 90, SCREEN_WIDTH - 2 * margin, 80)
        s = pygame.Surface((info_bg_rect.width, info_bg_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 128))  # Preto com 50% de transparência
        
        # Desenha o fundo com bordas arredondadas
        pygame.draw.rect(s, (0, 0, 0, 128), pygame.Rect(0, 0, info_bg_rect.width, info_bg_rect.height), border_radius=15)
        self.screen.blit(s, info_bg_rect)
        
        # Adiciona uma borda dourada fina
        pygame.draw.rect(self.screen, GOLD, info_bg_rect, 2, border_radius=15)
        
        label_surface = self.custom_font.render(label, True, WHITE)
        score_surface = self.custom_font.render(score_text, True, WHITE)
        status_surface = self.custom_font.render(status_text, True, WHITE)
        
        self.screen.blit(label_surface, (50, y_pos - 80))
        self.screen.blit(score_surface, (50, y_pos - 45))
        self.screen.blit(status_surface, (350, y_pos - 45))
        
        # Calcula o espaçamento correto entre as cartas
        card_spacing = int(self.card_sprites.card_width * self.card_scale * 0.5)
        
        for i, card in enumerate(player.hand):
            # Se for o oponente e o jogo não estiver terminado, mostra apenas o fundo da carta
            if not is_local and self.game_state == "PLAYING":
                # Obtém a sprite do verso da carta
                back_sprite = self.card_sprites.get_back_sprite()
                
                if back_sprite:
                    # Calcula o novo tamanho da carta
                    scaled_width = int(self.card_sprites.card_width * self.card_scale)
                    scaled_height = int(self.card_sprites.card_height * self.card_scale)
                    
                    # Redimensiona a sprite
                    scaled_sprite = pygame.transform.scale(back_sprite, (scaled_width, scaled_height))
                    
                    # Desenha o verso da carta
                    self.screen.blit(scaled_sprite, (50 + i * card_spacing, y_pos))
                else:
                    # Fallback para desenho manual se a sprite não for encontrada
                    rect = pygame.Rect(50 + i * card_spacing, y_pos, CARD_WIDTH, CARD_HEIGHT)
                    pygame.draw.rect(self.screen, BLUE, rect)
                    pygame.draw.rect(self.screen, BLACK, rect, 2)
            else:
                # Desenha a carta normalmente (para o jogador local ou quando o jogo terminar)
                self.draw_card(card, (50 + i * card_spacing, y_pos))
    
    def draw_buttons(self, player_status):
        # Só mostra os botões se o jogador ainda estiver jogando
        if player_status == "playing":
            pygame.draw.rect(self.screen, GOLD, self.hit_button, border_radius=8)
            pygame.draw.rect(self.screen, BLACK, self.hit_button, 4, border_radius=10)  # Contorno preto
            hit_text = self.custom_font.render("Mais Uma", True, BLACK)
            hit_text_rect = hit_text.get_rect(center=self.hit_button.center)
            self.screen.blit(hit_text, hit_text_rect)
            
            pygame.draw.rect(self.screen, GOLD, self.stand_button, border_radius=8)
            pygame.draw.rect(self.screen, BLACK, self.stand_button, 4, border_radius=10)  # Contorno preto
            stand_text = self.custom_font.render("Parar", True, BLACK)
            stand_text_rect = stand_text.get_rect(center=self.stand_button.center)
            self.screen.blit(stand_text, stand_text_rect)
    
    def draw_waiting_screen(self, menu):
        # Usa a imagem de fundo em vez de preenchimento sólido
        self.screen.blit(self.background_image, (0, 0))
        
        # Centraliza o texto "Aguardando um corajoso..."
        waiting_text = self.custom_font.render("Aguardando um corajoso...", True, WHITE)
        waiting_rect = waiting_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 30))
        self.screen.blit(waiting_text, waiting_rect)
        
        # Centraliza as informações de IP e porta
        ip_info = socket.gethostbyname(socket.gethostname())
        ip_text = self.small_custom_font.render(f"Sua mesa: {ip_info}", True, WHITE)
        ip_rect = ip_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 30))
        self.screen.blit(ip_text, ip_rect)
        
        port_text = self.small_custom_font.render(f"Cadeira: 5000", True, WHITE)
        port_rect = port_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(port_text, port_rect)
        
        # Botão Voltar
        pygame.draw.rect(self.screen, GOLD, menu.back_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, menu.back_button, 4, border_radius=10)  # Contorno preto
        back_text = self.custom_font.render("Voltar", True, BLACK)
        back_text_rect = back_text.get_rect(center=menu.back_button.center)
        self.screen.blit(back_text, back_text_rect)
    
    def draw_game_over(self, winner_text, is_host=True):
        # Atualiza o estado do jogo
        self.game_state = "GAME_OVER"
        self.game_over = True
        
        # Cria um painel semitransparente para o game over
        panel_width, panel_height = 500, 250  # Aumentado para acomodar os botões
        panel_rect = pygame.Rect(
            SCREEN_WIDTH//2 - panel_width//2,
            SCREEN_HEIGHT//2 - panel_height//2,
            panel_width,
            panel_height
        )
        
        # Desenha o painel com transparência
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 192))  # Preto com 75% de transparência
        self.screen.blit(s, panel_rect)
        pygame.draw.rect(self.screen, GOLD, panel_rect, 4, border_radius=15)  # Borda dourada
        
        # Textos traduzidos e centralizados
        game_over_text = self.title_font.render("Fim de Jogo!", True, WHITE)
        result_text = self.custom_font.render(winner_text, True, WHITE)
        
        # Posicionamento dos textos
        game_over_rect = game_over_text.get_rect(center=(SCREEN_WIDTH // 2, panel_rect.y + 50))
        result_rect = result_text.get_rect(center=(SCREEN_WIDTH // 2, panel_rect.y + 100))
        
        # Renderiza os textos
        self.screen.blit(game_over_text, game_over_rect)
        self.screen.blit(result_text, result_rect)
        
        # Adiciona botões para o host
        if is_host:
            button_width = 200
            button_height = 50
            button_y = panel_rect.y + 160
            button_margin = 20
            
            # Botão "Nova Partida"
            self.new_game_button = pygame.Rect(
                panel_rect.centerx - button_width - button_margin,
                button_y,
                button_width,
                button_height
            )
            
            # Botão "Sair da Mesa"
            self.exit_room_button = pygame.Rect(
                panel_rect.centerx + button_margin,
                button_y,
                button_width,
                button_height
            )
            
            # Desenha os botões
            pygame.draw.rect(self.screen, GOLD, self.new_game_button, border_radius=8)
            pygame.draw.rect(self.screen, BLACK, self.new_game_button, 4, border_radius=10)  # Contorno preto
            new_game_text = self.custom_font.render("Nova Partida", True, BLACK)
            new_game_rect = new_game_text.get_rect(center=self.new_game_button.center)
            self.screen.blit(new_game_text, new_game_rect)
            
            pygame.draw.rect(self.screen, GOLD, self.exit_room_button, border_radius=8)
            pygame.draw.rect(self.screen, BLACK, self.exit_room_button, 4, border_radius=10)  # Contorno preto
            exit_room_text = self.custom_font.render("Sair da Mesa", True, BLACK)
            exit_room_rect = exit_room_text.get_rect(center=self.exit_room_button.center)
            self.screen.blit(exit_room_text, exit_room_rect)
        else:
            # Texto de instrução para os não-hosts
            restart_text = self.small_custom_font.render("Aguardando o host iniciar nova partida ou pressione Q para sair", True, WHITE)
            restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, panel_rect.y + 170))
            self.screen.blit(restart_text, restart_rect)
    
    def reset_game_state(self):
        """Reseta o estado do jogo para o início de uma nova partida"""
        self.game_state = "PLAYING"
        self.game_over = False
    
    def draw_game(self, local_player, remote_player):
        # Usa a imagem de fundo em vez de preenchimento sólido
        self.screen.blit(self.background_image, (0, 0))
        
        # Atualiza o estado do jogo
        # Se o jogo estiver em PLAYING, garantimos que o estado do renderer também esteja em PLAYING
        if self.game_state != "GAME_OVER":
            self.game_state = "PLAYING"
            self.game_over = False
        
        self.draw_hand(local_player, True)
        self.draw_hand(remote_player, False)
        self.draw_buttons(local_player.status) 