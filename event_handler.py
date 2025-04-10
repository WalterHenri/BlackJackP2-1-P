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
            elif self.game.menu.settings_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.SETTINGS
            elif self.game.menu.exit_button.collidepoint(mouse_pos):
                pygame.quit()
                exit()
    
    def handle_settings_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Botões de Som
            if self.game.settings.sound_on_button.collidepoint(mouse_pos):
                self.game.settings.sound_enabled = True
            elif self.game.settings.sound_off_button.collidepoint(mouse_pos):
                self.game.settings.sound_enabled = False
            
            # Iniciar arrasto do slider de volume
            elif self.game.settings.slider_rect.collidepoint(mouse_pos) or self.game.settings.slider_button_rect.collidepoint(mouse_pos):
                self.game.settings.dragging_slider = True
                # Atualiza o slider com a posição atual do mouse
                self.game.settings.update_slider_position(mouse_pos[0])
                # Aplica o novo volume à música
                self.game.sound_manager.adjust_music_volume(self.game.settings.music_volume / 100)
                # Atualiza o estado da música (ligado/desligado)
                if self.game.settings.music_volume == 0:
                    self.game.sound_manager.stop_music()
                elif not pygame.mixer.music.get_busy() and self.game.settings.music_enabled:
                    self.game.sound_manager.play_random_music()
            
            # Botão Voltar
            elif self.game.settings.back_button.collidepoint(mouse_pos):
                self.game.game_state = GameState.MENU
        
        # Quando o mouse se move enquanto está arrastando o slider
        elif event.type == pygame.MOUSEMOTION and self.game.settings.dragging_slider:
            # Atualiza a posição do slider
            self.game.settings.update_slider_position(event.pos[0])
            # Aplica o novo volume à música
            self.game.sound_manager.adjust_music_volume(self.game.settings.music_volume / 100)
            # Atualiza o estado da música (ligado/desligado)
            if self.game.settings.music_volume == 0 and pygame.mixer.music.get_busy():
                self.game.sound_manager.stop_music()
            elif self.game.settings.music_volume > 0 and not pygame.mixer.music.get_busy() and self.game.settings.music_enabled:
                self.game.sound_manager.play_random_music()
        
        # Quando solta o botão do mouse, para de arrastar o slider
        elif event.type == pygame.MOUSEBUTTONUP:
            self.game.settings.dragging_slider = False
    
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
        if event.type == pygame.MOUSEBUTTONDOWN and self.game.local_player.status == "playing":
            mouse_pos = pygame.mouse.get_pos()
            if self.game.renderer.hit_button.collidepoint(mouse_pos):
                self.game.hit()
            elif self.game.renderer.stand_button.collidepoint(mouse_pos):
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
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            
            # Verifica se é o host antes de processar os cliques nos botões
            is_host = self.game.network.is_host if hasattr(self.game.network, 'is_host') else False
            
            if is_host:
                # Botão Nova Partida
                if hasattr(self.game.renderer, 'new_game_button') and self.game.renderer.new_game_button.collidepoint(mouse_pos):
                    # Reinicia o jogo
                    self.game.restart_game()
                
                # Botão Sair da Mesa
                elif hasattr(self.game.renderer, 'exit_room_button') and self.game.renderer.exit_room_button.collidepoint(mouse_pos):
                    # Envia mensagem para o cliente antes de fechar a conexão
                    self.game.network.send_message({'type': 'host_left'})
                    
                    # Deleta a sala se for host
                    if self.game.room_client.room_id:
                        self.game.room_client.delete_room(self.game.room_client.room_id)
                    
                    # Fecha a conexão e volta ao menu de salas
                    self.game.network.close_connection()
                    self.game.game_state = GameState.ROOM_LIST
                    self.game.room_client.list_rooms() 