import pygame
import os

class SoundManager:
    """
    Classe responsável por gerenciar os sons do jogo.
    """
    def __init__(self, settings=None):
        """
        Inicializa o gerenciador de sons.
        
        Args:
            settings: Referência à classe Settings para verificar configurações de som
        """
        # Inicializa o mixer do pygame se ainda não estiver inicializado
        if not pygame.mixer.get_init():
            pygame.mixer.init()
            
        self.settings = settings
        
        # Carrega os sons do jogo
        self.sounds = {
            'card': pygame.mixer.Sound('assets/card-sound.mp3'),
        }
        
        # Define o volume padrão para os efeitos sonoros
        self.set_sound_volume(0.5)
        
        # Configuração para música de fundo (com múltiplas alternativas)
        self.music_options = [
            'assets/background-music.mp3',
            'assets/bg-music.mp3',
            'assets/music.mp3'
        ]
        self.background_music = self.find_music_file()
        self.music_volume = 0.3
        self.music_loaded = False
        
        # Inicializa a música de fundo, se habilitada e disponível
        if self.background_music:
            self.initialize_music()
        else:
            print("Aviso: Nenhum arquivo de música de fundo encontrado. " +
                 "Adicione um arquivo em uma das seguintes localizações: " + 
                 ", ".join(self.music_options))
    
    def find_music_file(self):
        """Procura um arquivo de música válido entre as opções disponíveis"""
        for music_file in self.music_options:
            if os.path.exists(music_file):
                return music_file
        return None
    
    def initialize_music(self):
        """Inicializa a música de fundo baseado nas configurações"""
        if not self.background_music:
            return
            
        try:
            # Verifica se a música está habilitada nas configurações
            music_enabled = True
            if self.settings and hasattr(self.settings, 'music_enabled'):
                music_enabled = self.settings.music_enabled
                
            if music_enabled:
                # Carrega e inicia a música de fundo
                pygame.mixer.music.load(self.background_music)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)  # -1 para reprodução em loop
                self.music_loaded = True
            else:
                # Garante que a música esteja parada se desabilitada
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
        except Exception as e:
            print(f"Erro ao inicializar música: {e}")
            self.music_loaded = False
    
    def set_sound_volume(self, volume):
        """Define o volume de todos os efeitos sonoros (0.0 a 1.0)"""
        for sound in self.sounds.values():
            sound.set_volume(volume)
    
    def set_music_volume(self, volume):
        """Define o volume da música de fundo (0.0 a 1.0)"""
        self.music_volume = volume
        if self.music_loaded:
            pygame.mixer.music.set_volume(volume)
    
    def update_music_state(self):
        """Atualiza o estado da música baseado nas configurações atuais"""
        if not self.background_music:
            return
            
        if self.settings and hasattr(self.settings, 'music_enabled'):
            if self.settings.music_enabled:
                # Se música habilitada mas não está tocando, inicia
                if not pygame.mixer.music.get_busy():
                    try:
                        pygame.mixer.music.load(self.background_music)
                        pygame.mixer.music.set_volume(self.music_volume)
                        pygame.mixer.music.play(-1)
                        self.music_loaded = True
                    except Exception as e:
                        print(f"Erro ao iniciar música: {e}")
                        self.music_loaded = False
            else:
                # Se música desabilitada mas está tocando, para
                if pygame.mixer.music.get_busy():
                    pygame.mixer.music.stop()
    
    def play_card_sound(self):
        """
        Reproduz o som de carta sendo virada, verificando se a opção está habilitada
        nas configurações.
        """
        # Verifica se as configurações permitem reproduzir o som
        if self.settings and hasattr(self.settings, 'sound_enabled'):
            if self.settings.sound_enabled:
                self.sounds['card'].play()
        else:
            # Se não tiver acesso às configurações, reproduz o som por padrão
            self.sounds['card'].play()
    
    def play_sound(self, sound_name):
        """
        Reproduz um som pelo nome.
        
        Args:
            sound_name: Nome do som a ser reproduzido
        """
        if sound_name in self.sounds:
            # Somente reproduz se o som estiver habilitado
            if self.settings and hasattr(self.settings, 'sound_enabled'):
                if self.settings.sound_enabled:
                    self.sounds[sound_name].play()
            else:
                self.sounds[sound_name].play() 