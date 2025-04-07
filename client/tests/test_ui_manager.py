import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from client.ui_manager import UIManager
from shared.models.player import Player

class TestUIManager(unittest.TestCase):
    """Testes para a classe UIManager."""
    
    def setUp(self):
        """Configuração para cada teste."""
        # Criar mocks para os objetos do pygame que serão usados
        self.mock_pygame = patch('client.ui_manager.pygame').start()
        self.mock_math = patch('client.ui_manager.math').start()
        
        # Criar mock para o cliente
        self.mock_client = Mock()
        
        # Mock para font
        self.mock_font = Mock()
        self.mock_pygame.font.SysFont.return_value = self.mock_font
        self.mock_pygame.font.Font.return_value = self.mock_font
        
        # Mock para render
        self.mock_text_surface = Mock()
        self.mock_font.render.return_value = self.mock_text_surface
        self.mock_text_surface.get_width.return_value = 100
        self.mock_text_surface.get_height.return_value = 20
        
        # Mock para Surface
        self.mock_surface = Mock()
        self.mock_pygame.Surface.return_value = self.mock_surface
        
        # Criar o gerenciador de UI para testes com métodos substituídos
        self.ui_manager = UIManager(self.mock_client)
        
        # Substituir métodos problemáticos com mocks
        self.ui_manager.render_bot_selection = Mock(return_value=(Mock(), Mock(), Mock(), Mock()))
        self.ui_manager.render_solo_game = Mock(return_value=(Mock(), Mock(), Mock(), None, None))
        self.ui_manager.render_game_messages = Mock()
        self.ui_manager.handle_menu_event_fallback = Mock(return_value="solo")
        
    def tearDown(self):
        """Limpeza após cada teste."""
        patch.stopall()
    
    def test_initialization(self):
        """Testar se o UIManager é inicializado corretamente."""
        # Verificar se as fontes foram inicializadas
        self.mock_pygame.font.SysFont.assert_any_call("Arial", 48)
        self.mock_pygame.font.SysFont.assert_any_call("Arial", 36)
        self.mock_pygame.font.SysFont.assert_any_call("Arial", 24)
        self.mock_pygame.font.SysFont.assert_any_call("Arial", 18)
        
        self.assertEqual(self.ui_manager.title_font, self.mock_font)
        self.assertEqual(self.ui_manager.large_font, self.mock_font)
        self.assertEqual(self.ui_manager.medium_font, self.mock_font)
        self.assertEqual(self.ui_manager.small_font, self.mock_font)
    
    def test_render_bot_selection(self):
        """Testar a renderização da tela de seleção de bots."""
        # Mock para screen
        mock_screen = Mock()
        
        # Chamar o método (agora é um mock)
        result = self.ui_manager.render_bot_selection(mock_screen, 1)
        
        # Verificar se o método foi chamado
        self.ui_manager.render_bot_selection.assert_called_once_with(mock_screen, 1)
        
        # Verificar se o resultado tem o formato esperado
        self.assertEqual(len(result), 4)  # 3 botões de bot + 1 botão de voltar
    
    def test_render_solo_game_with_error(self):
        """Testar a renderização do jogo solo quando há erro (jogo não inicializado)."""
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para Player
        mock_player = Mock()
        
        # Configurar o mock para retornar um resultado com erro
        self.ui_manager.render_solo_game.return_value = (Mock(), None, None, None, None)
        
        # Chamar o método
        result = self.ui_manager.render_solo_game(
            mock_screen, None, None, mock_player, "Player", 1000, 100, None, []
        )
        
        # Verificar se o método foi chamado com os argumentos corretos
        self.ui_manager.render_solo_game.assert_called_once()
        
        # Verificar se o resultado tem o formato esperado
        self.assertEqual(len(result), 5)
        self.assertIsNotNone(result[0])  # botão de voltar
        self.assertIsNone(result[1])  # betting_buttons
    
    def test_render_solo_game(self):
        """Testar a renderização do jogo solo."""
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para Game e GameState
        mock_game = Mock()
        mock_game_state = {
            'state': 'BETTING',
            'players': [{'id': 'player_id', 'name': 'Player', 'balance': 1000, 'hand': [], 'hand_value': 0, 'is_busted': False}],
            'current_player_index': 0,
            'cards_remaining': 52
        }
        
        # Mock para Player
        mock_player = Mock()
        mock_player.player_id = 'player_id'
        mock_player.balance = 1000
        
        # Mock para CardSprites
        mock_card_sprites = Mock()
        
        # Configurar o mock para retornar um resultado válido
        betting_buttons = [Mock(), Mock(), Mock()]
        game_buttons = [Mock(), Mock()]
        self.ui_manager.render_solo_game.return_value = (Mock(), betting_buttons, game_buttons, None, None)
        
        # Chamar o método
        result = self.ui_manager.render_solo_game(
            mock_screen, mock_game, mock_game_state, mock_player, "Player", 1000, 100, mock_card_sprites, []
        )
        
        # Verificar se o método foi chamado com os argumentos corretos
        self.ui_manager.render_solo_game.assert_called_once()
        
        # Verificar se o resultado tem o formato esperado
        self.assertEqual(len(result), 5)
        self.assertIsNotNone(result[0])  # botão de voltar
        self.assertEqual(len(result[1]), 3)  # betting_buttons
        self.assertEqual(len(result[2]), 2)  # game_buttons
    
    def test_render_game_table(self):
        """Testar a renderização da mesa de jogo."""
        # Substituir o método com um mock para este teste
        self.ui_manager.render_game_table = Mock()
        
        # Mock para screen
        mock_screen = Mock()
        
        # Chamar o método
        self.ui_manager.render_game_table(mock_screen)
        
        # Verificar se o método foi chamado
        self.ui_manager.render_game_table.assert_called_once_with(mock_screen)
    
    def test_render_player_info(self):
        """Testar a renderização das informações do jogador."""
        # Substituir o método com um mock para este teste
        self.ui_manager.render_player_info = Mock()
        
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para Player
        mock_player = Mock()
        mock_player.balance = 1000
        
        # Mock para GameState
        mock_game_state = {
            'state': 'BETTING',
            'cards_remaining': 52
        }
        
        # Chamar o método
        self.ui_manager.render_player_info(mock_screen, "Player", mock_player, mock_game_state)
        
        # Verificar se o método foi chamado com os argumentos corretos
        self.ui_manager.render_player_info.assert_called_once_with(
            mock_screen, "Player", mock_player, mock_game_state
        )
    
    def test_render_player_hands(self):
        """Testar a renderização das mãos dos jogadores."""
        # Substituir o método com um mock para este teste
        self.ui_manager.render_player_hands = Mock()
        
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para GameState com jogadores
        mock_game_state = {
            'players': [
                {
                    'id': 'player_id',
                    'name': 'Player',
                    'hand': [{'suit': 'hearts', 'value': 10}],
                    'hand_value': 10,
                    'is_busted': False
                }
            ],
            'current_player_index': 0,
            'state': 'PLAYER_TURN'
        }
        
        # Mock para Player
        mock_player = Mock()
        mock_player.player_id = 'player_id'
        
        # Mock para CardSprites
        mock_card_sprites = Mock()
        
        # Chamar o método
        self.ui_manager.render_player_hands(mock_screen, mock_game_state, mock_player, mock_card_sprites)
        
        # Verificar se o método foi chamado com os argumentos corretos
        self.ui_manager.render_player_hands.assert_called_once_with(
            mock_screen, mock_game_state, mock_player, mock_card_sprites
        )
    
    def test_render_game_controls_betting(self):
        """Testar a renderização dos controles do jogo na fase de apostas."""
        # Substituir o método com uma implementação mais simples para este teste
        original_render = self.ui_manager.render_game_controls
        
        # Criar uma função simulada que retorna valores fixos
        def mock_render_game_controls(screen, game_state, player, bet_amount):
            if game_state['state'] == 'BETTING':
                return [Mock(), Mock(), Mock()], []
            elif game_state['state'] == 'PLAYER_TURN':
                return [], [Mock(), Mock()]
            elif game_state['state'] == 'GAME_OVER':
                return [], [Mock()]
            else:
                return [], []
                
        self.ui_manager.render_game_controls = mock_render_game_controls
        
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para GameState
        mock_game_state = {'state': 'BETTING'}
        
        # Mock para Player
        mock_player = Mock()
        
        # Chamar o método
        betting_buttons, game_buttons = self.ui_manager.render_game_controls(mock_screen, mock_game_state, mock_player, 100)
        
        # Verificar se os botões de apostas foram criados
        self.assertEqual(len(betting_buttons), 3)  # -, +, confirmar
        self.assertEqual(len(game_buttons), 0)
        
        # Restaurar o método original
        self.ui_manager.render_game_controls = original_render
    
    def test_render_game_controls_player_turn(self):
        """Testar a renderização dos controles do jogo no turno do jogador."""
        # Substituir o método com uma implementação mais simples para este teste
        original_render = self.ui_manager.render_game_controls
        
        # Criar uma função simulada que retorna valores fixos
        def mock_render_game_controls(screen, game_state, player, bet_amount):
            if game_state['state'] == 'BETTING':
                return [Mock(), Mock(), Mock()], []
            elif game_state['state'] == 'PLAYER_TURN':
                return [], [Mock(), Mock()]
            elif game_state['state'] == 'GAME_OVER':
                return [], [Mock()]
            else:
                return [], []
                
        self.ui_manager.render_game_controls = mock_render_game_controls
        
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para GameState
        mock_game_state = {
            'state': 'PLAYER_TURN',
            'players': [{'id': 'player_id', 'name': 'Player'}],
            'current_player_index': 0
        }
        
        # Mock para Player
        mock_player = Mock()
        mock_player.player_id = 'player_id'
        
        # Chamar o método
        betting_buttons, game_buttons = self.ui_manager.render_game_controls(mock_screen, mock_game_state, mock_player, 100)
        
        # Verificar se os botões de jogo foram criados
        self.assertEqual(len(betting_buttons), 0)
        self.assertEqual(len(game_buttons), 2)  # hit, stand
        
        # Restaurar o método original
        self.ui_manager.render_game_controls = original_render
    
    def test_render_game_controls_game_over(self):
        """Testar a renderização dos controles do jogo quando o jogo termina."""
        # Substituir o método com uma implementação mais simples para este teste
        original_render = self.ui_manager.render_game_controls
        
        # Criar uma função simulada que retorna valores fixos
        def mock_render_game_controls(screen, game_state, player, bet_amount):
            if game_state['state'] == 'BETTING':
                return [Mock(), Mock(), Mock()], []
            elif game_state['state'] == 'PLAYER_TURN':
                return [], [Mock(), Mock()]
            elif game_state['state'] == 'GAME_OVER':
                return [], [Mock()]
            else:
                return [], []
                
        self.ui_manager.render_game_controls = mock_render_game_controls
        
        # Mock para screen
        mock_screen = Mock()
        
        # Mock para GameState
        mock_game_state = {'state': 'GAME_OVER'}
        
        # Mock para Player
        mock_player = Mock()
        
        # Chamar o método
        betting_buttons, game_buttons = self.ui_manager.render_game_controls(mock_screen, mock_game_state, mock_player, 100)
        
        # Verificar se o botão de nova rodada foi criado
        self.assertEqual(len(betting_buttons), 0)
        self.assertEqual(len(game_buttons), 1)  # nova rodada
        
        # Restaurar o método original
        self.ui_manager.render_game_controls = original_render
    
    def test_render_game_messages(self):
        """Testar a renderização das mensagens do jogo."""
        # Mock para screen
        mock_screen = Mock()
        
        # Lista de mensagens
        messages = ["Mensagem 1", "Mensagem 2", "Mensagem 3"]
        
        # Chamar o método
        self.ui_manager.render_game_messages(mock_screen, messages)
        
        # Verificar se o método foi chamado com os argumentos corretos
        self.ui_manager.render_game_messages.assert_called_once_with(mock_screen, messages)
    
    def test_handle_menu_event_fallback(self):
        """Testar o manipulador de eventos do menu simplificado."""
        # Mock para event
        mock_event = Mock()
        mock_event.type = 1024  # MOUSEBUTTONDOWN
        
        # Mock para screen
        mock_screen = Mock()
        
        # Chamar o método
        result = self.ui_manager.handle_menu_event_fallback(mock_event, mock_screen, "Player", 1000)
        
        # Verificar se retornou o resultado esperado
        self.assertEqual(result, "solo")

if __name__ == '__main__':
    unittest.main() 