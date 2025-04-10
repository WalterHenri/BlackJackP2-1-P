import pygame
import os
import random

class SoundManager:
    def __init__(self, settings=None):
        # Inicializar o mixer para reprodução de áudio
        pygame.mixer.init()
        
        # Armazenar referência às configurações do jogo
        self.settings = settings
        
        # Carregar os sons do jogo
        self.sounds = {
            'card': pygame.mixer.Sound('assets/card-sound.mp3')
        }
        
        # Ajustar volume inicial dos efeitos sonoros
        self.adjust_sound_volume(0.5)  # 50% do volume
        
        # Carregar músicas de fundo
        self.music_files = []
        self.load_music_files()
        
        # Controle de música
        self.current_music = None
        self.music_volume = 0.3  # 30% do volume
        pygame.mixer.music.set_volume(self.music_volume)
    
    def load_music_files(self):
        """
        Carrega todos os arquivos MP3 da pasta assets/musgas
        """
        music_dir = "assets/musgas"
        
        # Verifica se o diretório existe
        if not os.path.exists(music_dir):
            print(f"Diretório {music_dir} não encontrado.")
            return
        
        # Lista todos os arquivos .mp3 na pasta
        for file in os.listdir(music_dir):
            if file.lower().endswith('.mp3'):
                self.music_files.append(os.path.join(music_dir, file))
        
        print(f"Carregadas {len(self.music_files)} músicas.")
    
    def play_random_music(self):
        """
        Reproduz uma música aleatória da biblioteca se a música estiver habilitada
        """
        if not self.music_files:
            return
            
        if self.settings and hasattr(self.settings, 'music_enabled') and self.settings.music_enabled:
            # Escolhe uma música aleatória
            next_music = random.choice(self.music_files)
            
            # Carrega e toca a música
            pygame.mixer.music.load(next_music)
            pygame.mixer.music.play()
            
            # Armazena a música atual
            self.current_music = next_music
            
            print(f"Tocando: {os.path.basename(next_music)}")
    
    def stop_music(self):
        """
        Para a reprodução da música atual
        """
        pygame.mixer.music.stop()
        self.current_music = None
    
    def toggle_music(self):
        """
        Alterna a reprodução de música com base nas configurações
        """
        if self.settings and hasattr(self.settings, 'music_enabled'):
            if self.settings.music_enabled and not pygame.mixer.music.get_busy():
                self.play_random_music()
            elif not self.settings.music_enabled and pygame.mixer.music.get_busy():
                self.stop_music()
    
    def check_music_ended(self):
        """
        Verifica se a música atual terminou e inicia outra música aleatória
        Deve ser chamado no loop principal do jogo
        """
        if self.settings and hasattr(self.settings, 'music_enabled') and self.settings.music_enabled:
            if not pygame.mixer.music.get_busy() and self.current_music is not None:
                # A música acabou, toca outra
                self.play_random_music()
            elif self.current_music is None:
                # Nenhuma música tocando, inicia uma
                self.play_random_music()
    
    def play_card_sound(self):
        """
        Reproduz o som da carta sendo puxada, se estiver habilitado nas configurações
        """
        # Verifica se as configurações existem e o som está habilitado
        if self.settings and hasattr(self.settings, 'sound_enabled') and self.settings.sound_enabled:
            self.sounds['card'].play()
    
    def adjust_sound_volume(self, volume):
        """
        Ajusta o volume dos efeitos sonoros
        :param volume: Valor entre 0.0 e 1.0
        """
        for sound in self.sounds.values():
            sound.set_volume(volume)
    
    def adjust_music_volume(self, volume):
        """
        Ajusta o volume da música de fundo
        :param volume: Valor entre 0.0 e 1.0
        """
        self.music_volume = volume
        pygame.mixer.music.set_volume(volume) 