import pygame
from constants import *

class Menu:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        self.ip_input = ""
        self.ip_input_active = False
        self.port = 5000
        
        # Carrega a imagem de fundo
        self.background_image = pygame.image.load("assets/capa.jpg")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Carrega a fonte personalizada
        self.custom_font = pygame.font.Font("assets/font-jersey.ttf", 30)
        self.title_font = pygame.font.Font("assets/font-jersey.ttf", 80)
        
        # Button dimensions and positions
        button_width = 260
        button_height = 50
        button_margin = 20
        button_x = SCREEN_WIDTH * 0.7  # Posicionamento à direita como na imagem
        
        # Posições dos botões ajustadas para serem semelhantes à imagem
        self.start_button = pygame.Rect(
            button_x - button_width // 2,
            SCREEN_HEIGHT // 2 - 80,
            button_width, 
            button_height
        )
        
        self.join_button = pygame.Rect(
            button_x - button_width // 2,
            SCREEN_HEIGHT // 2,
            button_width, 
            button_height
        )
        
        self.settings_button = pygame.Rect(
            button_x - button_width // 2,
            SCREEN_HEIGHT // 2 + 80,
            button_width, 
            button_height
        )
        
        self.exit_button = pygame.Rect(
            button_x - button_width // 2,
            SCREEN_HEIGHT // 2 + 160,
            button_width, 
            button_height
        )
        
        # Mantendo os retângulos originais para manter a funcionalidade
        self.ip_input_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 200,
            SCREEN_HEIGHT // 2 - 30,
            400,
            60
        )
        
        self.back_button = pygame.Rect(
            50,
            SCREEN_HEIGHT - 100,
            120,
            50
        )
        
        self.connect_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 100,
            SCREEN_HEIGHT // 2 + 60,
            200,
            50
        )
        
        # Para compatibilidade com o código existente
        self.host_button = self.start_button
    
    def draw_menu(self):
        # Background com imagem
        self.screen.blit(self.background_image, (0, 0))
        
        # Host button
        pygame.draw.rect(self.screen, BLUE, self.host_button, border_radius=5)
        host_text = self.font.render("Host Game", True, WHITE)
        host_text_rect = host_text.get_rect(center=self.host_button.center)
        self.screen.blit(host_text, host_text_rect)
        
        # Botão "Começar Partida" (Host Game)
        pygame.draw.rect(self.screen, GOLD, self.start_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.start_button, 4, border_radius=10)  # Contorno preto
        start_text = self.custom_font.render("Começar Partida", True, BLACK)
        start_text_rect = start_text.get_rect(center=self.start_button.center)
        self.screen.blit(start_text, start_text_rect)
        
        # Botão "Entrar no Meio" (Join Game)
        pygame.draw.rect(self.screen, GOLD, self.join_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.join_button, 4, border_radius=10)  # Contorno preto
        join_text = self.custom_font.render("Entrar no Meio", True, BLACK)
        join_text_rect = join_text.get_rect(center=self.join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Botão "Ajeitar o Jogo" (Sem função)
        pygame.draw.rect(self.screen, GOLD, self.settings_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.settings_button, 4, border_radius=10)  # Contorno preto
        settings_text = self.custom_font.render("Ajeitar o Jogo", True, BLACK)
        settings_text_rect = settings_text.get_rect(center=self.settings_button.center)
        self.screen.blit(settings_text, settings_text_rect)
        
        # Botão "Ir ao Banheiro(sair)" (Sem função)
        pygame.draw.rect(self.screen, GOLD, self.exit_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.exit_button, 4, border_radius=10)  # Contorno preto
        exit_text = self.custom_font.render("Ir ao Banheiro(sair)", True, BLACK)
        exit_text_rect = exit_text.get_rect(center=self.exit_button.center)
        self.screen.blit(exit_text, exit_text_rect)
    
    def draw_join_screen(self):
        # Background com imagem
        self.screen.blit(self.background_image, (0, 0))
        
        # Title
        title_text = self.custom_font.render("Join Game", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # IP input box
        pygame.draw.rect(self.screen, WHITE, self.ip_input_rect, border_radius=5)
        if self.ip_input_active:
            pygame.draw.rect(self.screen, LIGHT_BLUE, self.ip_input_rect, 3, border_radius=5)
        else:
            pygame.draw.rect(self.screen, BLACK, self.ip_input_rect, 3, border_radius=5)
        
        # IP input text
        ip_text = self.font.render(self.ip_input if self.ip_input else "Enter host IP address", True, 
                                  BLACK if self.ip_input else (150, 150, 150))
        ip_text_rect = ip_text.get_rect(center=self.ip_input_rect.center)
        self.screen.blit(ip_text, ip_text_rect)
        
        # Connect button
        pygame.draw.rect(self.screen, BLUE, self.connect_button, border_radius=5)
        pygame.draw.rect(self.screen, BLACK, self.connect_button, 2, border_radius=5)  # Contorno preto
        connect_text = self.custom_font.render("Connect", True, WHITE)
        connect_text_rect = connect_text.get_rect(center=self.connect_button.center)
        self.screen.blit(connect_text, connect_text_rect)
        
        # Back button
        pygame.draw.rect(self.screen, RED, self.back_button, border_radius=5)
        pygame.draw.rect(self.screen, BLACK, self.back_button, 2, border_radius=5)  # Contorno preto
        back_text = self.custom_font.render("Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect)
        
        # Port text
        port_text = self.small_font.render(f"Port: {self.port}", True, WHITE)
        self.screen.blit(port_text, (SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT // 2 + 120)) 