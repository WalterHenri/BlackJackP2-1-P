import pygame
from constants import GameState

class EventHandler:
    def __init__(self, game):
        self.game = game
    
    def handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.host_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.CREATE_ROOM
                self.game.room_menu.room_name_input = ""
                self.game.room_menu.room_name_active = True
            elif self.game.menu.join_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.ROOM_LIST
                self.game.room_client.list_rooms()
    
    def handle_join_screen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.ip_input_rect.collidepoint(mouse_pos):
                self.game.menu.ip_input_active = True
            else:
                self.game.menu.ip_input_active = False
            
            if self.game.menu.back_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.ROOM_LIST
                self.game.room_client.list_rooms()
            
            if self.game.menu.connect_button.collidepoint(mouse_pos) and self.game.menu.ip_input:
                self.game.initialize_game(is_host=False, peer_address=self.game.menu.ip_input)
        
        if event.type == pygame.KEYDOWN and self.game.menu.ip_input_active:
            if event.key == pygame.K_RETURN:
                if self.game.menu.ip_input:
                    self.game.initialize_game(is_host=False, peer_address=self.game.menu.ip_input)
            elif event.key == pygame.K_BACKSPACE:
                self.game.menu.ip_input = self.game.menu.ip_input[:-1]
            else:
                self.game.menu.ip_input += event.unicode
    
    def handle_waiting_screen_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.menu.back_button.collidepoint(mouse_pos):
                if self.game.room_client.is_host and self.game.room_client.room_id:
                    self.game.room_client.delete_room(self.game.room_client.room_id)
                
                self.game.network.close_connection()
                self.game.game_state = GameState.ROOM_LIST
                self.game.room_client.list_rooms()
    
    def handle_playing_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if self.game.renderer.hit_button.collidepoint(mouse_pos) and self.game.local_player.status == "playing":
                self.game.hit()
            elif self.game.renderer.stand_button.collidepoint(mouse_pos) and self.game.local_player.status == "playing":
                self.game.stand()
    
    def handle_game_over_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:  # Restart
                # Reset game
                self.game.restart_game()
            elif event.key == pygame.K_q or event.key == pygame.K_m:  # Quit/Menu
                if self.game.room_client.is_host and self.game.room_client.room_id:
                    self.game.room_client.delete_room(self.game.room_client.room_id)
                
                self.game.network.close_connection()
                self.game.game_state = GameState.ROOM_LIST
                self.game.room_client.list_rooms() 