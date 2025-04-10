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
        
        # Button dimensions and positions
        button_width = 300
        button_height = 60
        button_margin = 30
        
        self.host_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 - button_height - button_margin,
            button_width, 
            button_height
        )
        
        self.join_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width // 2,
            SCREEN_HEIGHT // 2 + button_margin,
            button_width, 
            button_height
        )
        
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
    
    def draw_menu(self):
        # Background
        self.screen.fill(GREEN)
        
        # Title
        title_text = self.font.render("21 Blackjack - P2P", True, GOLD)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Host button
        pygame.draw.rect(self.screen, BLUE, self.host_button, border_radius=5)
        host_text = self.font.render("Host Game", True, WHITE)
        host_text_rect = host_text.get_rect(center=self.host_button.center)
        self.screen.blit(host_text, host_text_rect)
        
        # Join button
        pygame.draw.rect(self.screen, RED, self.join_button, border_radius=5)
        join_text = self.font.render("Join Game", True, WHITE)
        join_text_rect = join_text.get_rect(center=self.join_button.center)
        self.screen.blit(join_text, join_text_rect)
        
        # Instructions
        instructions_text = self.small_font.render("Choose to host a new game or join an existing one", True, WHITE)
        self.screen.blit(instructions_text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT - 100))
    
    def draw_join_screen(self):
        # Background
        self.screen.fill(GREEN)
        
        # Title
        title_text = self.font.render("Join Game", True, WHITE)
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
        connect_text = self.font.render("Connect", True, WHITE)
        connect_text_rect = connect_text.get_rect(center=self.connect_button.center)
        self.screen.blit(connect_text, connect_text_rect)
        
        # Back button
        pygame.draw.rect(self.screen, RED, self.back_button, border_radius=5)
        back_text = self.font.render("Back", True, WHITE)
        back_text_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_text_rect)
        
        # Port text
        port_text = self.small_font.render(f"Port: {self.port}", True, WHITE)
        self.screen.blit(port_text, (SCREEN_WIDTH // 2 - 40, SCREEN_HEIGHT // 2 + 120)) 