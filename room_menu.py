import pygame
import socket
from constants import *

class RoomMenu:
    def __init__(self, screen, font, small_font):
        self.screen = screen
        self.font = font
        self.small_font = small_font
        
        # Carrega a imagem de fundo
        self.background_image = pygame.image.load("assets/capa2.png")
        self.background_image = pygame.transform.scale(self.background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
        
        # Carrega a fonte personalizada
        self.custom_font = pygame.font.Font("assets/font-jersey.ttf", 30)
        self.small_custom_font = pygame.font.Font("assets/font-jersey.ttf", 20)
        self.title_font = pygame.font.Font("assets/font-jersey.ttf", 40)
        
        # Estado do menu de salas
        self.rooms = []  # Lista de salas disponíveis
        self.selected_room_index = -1
        self.scroll_offset = 0
        self.max_visible_rooms = 6
        
        # Para criação de sala
        self.room_name_input = ""
        self.room_name_active = False
        
        # Elementos da UI
        self.create_ui_elements()
    
    def create_ui_elements(self):
        """Cria os elementos de interface do usuário"""
        # Área de listagem de salas
        self.room_list_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 300,
            120,
            600,
            SCREEN_HEIGHT - 300
        )
        
        # Botão atualizar alinhado com a borda direita da lista
        self.refresh_button = pygame.Rect(
            self.room_list_rect.x + self.room_list_rect.width - 120,  # Posicionado na borda direita da lista
            self.room_list_rect.y - 50,  # 50px acima da lista
            120, 
            40
        )
        
        button_y_bottom = SCREEN_HEIGHT - 80
        self.back_button = pygame.Rect(
            50,
            button_y_bottom,
            120,
            50
        )
        
        # Botões logo abaixo da lista de salas
        button_width = 150
        button_margin = 20
        button_y = self.room_list_rect.y + self.room_list_rect.height + 20  
        
        self.create_room_button = pygame.Rect(
            SCREEN_WIDTH // 2 - button_width - button_margin // 2,
            button_y,
            button_width,
            50
        )
        
        self.join_room_button = pygame.Rect(
            SCREEN_WIDTH // 2 + button_margin // 2,
            button_y,
            button_width,
            50
        )
        
        # Entrada de texto para nome da sala
        self.room_name_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 200,
            SCREEN_HEIGHT // 2 - 30,
            400,
            60
        )
        
        # Botão de confirmar criação de sala
        self.confirm_create_button = pygame.Rect(
            SCREEN_WIDTH // 2 - 100,
            SCREEN_HEIGHT // 2 + 60,
            200,
            50
        )
    
    def draw_room_list(self, title="Salas Disponíveis"):
        """Desenha a lista de salas disponíveis"""
        # Usa a imagem de fundo em vez de preenchimento sólido
        self.screen.blit(self.background_image, (0, 0))
        
        # Título
        title_text = self.title_font.render(title, True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 50))
        self.screen.blit(title_text, title_rect)
        
        # Fundo da lista de salas
        pygame.draw.rect(self.screen, DARK_GREEN, self.room_list_rect, border_radius=5)
        pygame.draw.rect(self.screen, BLACK, self.room_list_rect, 2, border_radius=5)
        
        # Botão de atualizar
        pygame.draw.rect(self.screen, GOLD, self.refresh_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.refresh_button, 4, border_radius=10)  # Contorno preto
        refresh_text = self.small_custom_font.render("Atualizar", True, BLACK)
        refresh_rect = refresh_text.get_rect(center=self.refresh_button.center)
        self.screen.blit(refresh_text, refresh_rect)
        
        # Desenhar salas
        if not self.rooms:
            no_rooms_text = self.custom_font.render("Nenhuma sala disponível", True, WHITE)
            no_rooms_rect = no_rooms_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            self.screen.blit(no_rooms_text, no_rooms_rect)
        else:
            visible_end = min(len(self.rooms), self.scroll_offset + self.max_visible_rooms)
            visible_rooms = self.rooms[self.scroll_offset:visible_end]
            
            for i, room in enumerate(visible_rooms):
                room_rect = pygame.Rect(
                    self.room_list_rect.x + 10,
                    self.room_list_rect.y + 10 + i * 60,
                    self.room_list_rect.width - 20,
                    50
                )
                
                # Destacar a sala selecionada
                if i + self.scroll_offset == self.selected_room_index:
                    pygame.draw.rect(self.screen, LIGHT_BLUE, room_rect, border_radius=5)
                else:
                    pygame.draw.rect(self.screen, WHITE, room_rect, border_radius=5)
                
                pygame.draw.rect(self.screen, BLACK, room_rect, 1, border_radius=5)
                
                # Nome da sala
                room_name = room.get('name', 'Sala sem nome')
                room_id = room.get('id', '')
                room_host = room.get('host', 'Desconhecido')
                
                name_text = self.custom_font.render(room_name, True, BLACK)
                id_text = self.small_custom_font.render(f"ID: {room_id}", True, BLACK)
                host_text = self.small_custom_font.render(f"Host: {room_host}", True, BLACK)
                
                self.screen.blit(name_text, (room_rect.x + 10, room_rect.y + 5))
                self.screen.blit(id_text, (room_rect.x + 10, room_rect.y + 30))
                self.screen.blit(host_text, (room_rect.x + 200, room_rect.y + 30))
        
        # Botão para criar sala
        pygame.draw.rect(self.screen, GOLD, self.create_room_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.create_room_button, 4, border_radius=10)  # Contorno preto
        create_text = self.custom_font.render("Criar Sala", True, BLACK)
        create_rect = create_text.get_rect(center=self.create_room_button.center)
        self.screen.blit(create_text, create_rect)
        
        # Botão para entrar na sala
        button_color = GOLD if self.selected_room_index >= 0 else GRAY
        pygame.draw.rect(self.screen, button_color, self.join_room_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.join_room_button, 4, border_radius=10)  # Contorno preto
        join_text = self.custom_font.render("Entrar", True, BLACK)
        join_rect = join_text.get_rect(center=self.join_room_button.center)
        self.screen.blit(join_text, join_rect)
        
        # Botão de voltar
        pygame.draw.rect(self.screen, GOLD, self.back_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.back_button, 4, border_radius=10)  # Contorno preto
        back_text = self.custom_font.render("Voltar", True, BLACK)
        back_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_rect)
    
    def draw_create_room(self):
        """Desenha a tela de criação de sala"""
        # Usa a imagem de fundo em vez de preenchimento sólido
        self.screen.blit(self.background_image, (0, 0))
        
        # Título
        title_text = self.title_font.render("Criar Nova Sala", True, WHITE)
        title_rect = title_text.get_rect(center=(SCREEN_WIDTH // 2, 100))
        self.screen.blit(title_text, title_rect)
        
        # Campo de entrada do nome da sala
        pygame.draw.rect(self.screen, WHITE, self.room_name_rect, border_radius=8)
        if self.room_name_active:
            pygame.draw.rect(self.screen, LIGHT_BLUE, self.room_name_rect, 4, border_radius=10)
        else:
            pygame.draw.rect(self.screen, BLACK, self.room_name_rect, 4, border_radius=10)
        
        # Texto do campo de entrada
        room_name_text = self.custom_font.render(
            self.room_name_input if self.room_name_input else "Digite o nome da sala",
            True,
            BLACK if self.room_name_input else (150, 150, 150)
        )
        room_name_rect = room_name_text.get_rect(center=self.room_name_rect.center)
        self.screen.blit(room_name_text, room_name_rect)
        
        # Botão de confirmar
        button_color = GOLD if self.room_name_input else GRAY
        pygame.draw.rect(self.screen, button_color, self.confirm_create_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.confirm_create_button, 4, border_radius=10)  # Contorno preto
        confirm_text = self.custom_font.render("Criar", True, BLACK)
        confirm_rect = confirm_text.get_rect(center=self.confirm_create_button.center)
        self.screen.blit(confirm_text, confirm_rect)
        
        # Botão de voltar
        pygame.draw.rect(self.screen, GOLD, self.back_button, border_radius=8)
        pygame.draw.rect(self.screen, BLACK, self.back_button, 4, border_radius=10)  # Contorno preto
        back_text = self.custom_font.render("Voltar", True, BLACK)
        back_rect = back_text.get_rect(center=self.back_button.center)
        self.screen.blit(back_text, back_rect)
    
    def update_rooms(self, rooms):
        """Atualiza a lista de salas"""
        self.rooms = rooms
        
        # Verificar se a sala selecionada ainda está disponível
        if self.selected_room_index >= len(self.rooms):
            self.selected_room_index = -1
    
    def handle_room_list_event(self, event):
        """Processa eventos na tela de lista de salas"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Verificar clique em salas
            if self.room_list_rect.collidepoint(mouse_pos) and self.rooms:
                visible_end = min(len(self.rooms), self.scroll_offset + self.max_visible_rooms)
                visible_rooms = self.rooms[self.scroll_offset:visible_end]
                
                for i, _ in enumerate(visible_rooms):
                    room_rect = pygame.Rect(
                        self.room_list_rect.x + 10,
                        self.room_list_rect.y + 10 + i * 60,
                        self.room_list_rect.width - 20,
                        50
                    )
                    
                    if room_rect.collidepoint(mouse_pos):
                        self.selected_room_index = i + self.scroll_offset
                        return None  # Nenhuma ação, apenas seleção
            
            # Verificar clique em botões
            if self.refresh_button.collidepoint(mouse_pos):
                return "refresh"
            
            if self.create_room_button.collidepoint(mouse_pos):
                return "create_room"
            
            if self.join_room_button.collidepoint(mouse_pos) and self.selected_room_index >= 0:
                return "join_room"
            
            if self.back_button.collidepoint(mouse_pos):
                return "back"
        
        # Rolagem da lista
        elif event.type == pygame.MOUSEWHEEL:
            if self.rooms:
                self.scroll_offset = max(0, min(len(self.rooms) - self.max_visible_rooms, self.scroll_offset - event.y))
        
        return None
    
    def handle_create_room_event(self, event):
        """Processa eventos na tela de criação de sala"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Verificar clique no campo de texto
            if self.room_name_rect.collidepoint(mouse_pos):
                self.room_name_active = True
            else:
                self.room_name_active = False
            
            # Verificar clique em botões
            if self.confirm_create_button.collidepoint(mouse_pos) and self.room_name_input:
                return "confirm_create"
            
            if self.back_button.collidepoint(mouse_pos):
                return "back"
        
        # Entrada de texto
        elif event.type == pygame.KEYDOWN and self.room_name_active:
            if event.key == pygame.K_RETURN and self.room_name_input:
                return "confirm_create"
            elif event.key == pygame.K_BACKSPACE:
                self.room_name_input = self.room_name_input[:-1]
            else:
                self.room_name_input += event.unicode
        
        return None
    
    def get_selected_room(self):
        """Retorna a sala selecionada"""
        if 0 <= self.selected_room_index < len(self.rooms):
            return self.rooms[self.selected_room_index]
        return None 