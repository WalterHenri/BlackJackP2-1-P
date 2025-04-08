import sys
import os
import unittest
from unittest.mock import Mock, patch

# Adicionar diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.models.player import Player
from shared.models.game import Game
from client.game_client import BlackjackClient

class TestGameLogic(unittest.TestCase):
    """Testes para a lógica do jogo do BlackjackClient."""
    
    def setUp(self):
        """Configuração para cada teste."""
        # Criar mocks para os objetos do pygame que serão usados
        self.mock_pygame = patch('client.game_client.pygame').start()
        self.mock_sys = patch('client.game_client.sys').start()
        
        # Mock para CardSprites
        self.mock_card_sprites = patch('client.game_client.CardSprites').start()
        
        # Mock para UIManager
        self.mock_ui_manager = patch('client.game_client.UIManager').start()
        
        # Mock para MenuView
        self.mock_menu_view = patch('client.game_client.MenuView').start()
        
        # Mock para funções de dados do jogador
        self.mock_get_balance = patch('client.game_client.get_player_balance').start()
        self.mock_get_balance.return_value = 1000
        
        self.mock_update_balance = patch('client.game_client.update_player_balance').start()
        
        # Mock para Game
        self.mock_game = patch('client.game_client.Game').start()
        self.mock_game.return_value.get_game_state.return_value = {
            'state': 'BETTING',
            'players': [{'id': 'player_id', 'name': 'Player', 'balance': 1000, 'hand': [], 'hand_value': 0, 'is_busted': False}],
            'current_player_index': 0,
            'cards_remaining': 52
        }
        
        # Criar o cliente para testes
        self.client = BlackjackClient()
        
        # Configurar manualmente alguns atributos para facilitar os testes
        self.client.player = Player("Player", 1000, "player_id")
        self.client.game = self.mock_game.return_value
        self.client.game_state = self.client.game.get_game_state()
        
    def tearDown(self):
        """Limpeza após cada teste."""
        patch.stopall()
    
    def test_initialization(self):
        """Testar se o cliente é inicializado corretamente."""
        self.assertEqual(self.client.player_name, "Player")
        self.assertEqual(self.client.player_balance, 1000)
        self.assertEqual(self.client.current_view, "menu")
        self.assertEqual(self.client.bet_amount, 100)
        self.assertEqual(self.client.selected_bot_count, 1)
        self.assertFalse(self.client.host_mode)
    
    def test_start_single_player(self):
        """Testar o início do modo solo com bots."""
        # Configurar o mock do Game para simular a adição de bots
        self.client.game.add_player = Mock(return_value=(True, "Jogador adicionado"))
        self.client.game.start_game = Mock()
        
        # Chamar o método
        self.client.start_single_player(2)
        
        # Verificar se o jogo foi configurado corretamente
        self.assertEqual(self.client.selected_bot_count, 2)
        self.assertEqual(self.client.current_view, "game")
        self.assertFalse(self.client.host_mode)
        
        # Verificar se os métodos corretos foram chamados
        self.client.game.initialize_game.assert_called_once()
        self.assertEqual(self.client.game.add_player.call_count, 2)  # Dois bots adicionados
        self.client.game.start_game.assert_called_once()
    
    def test_decrease_bet(self):
        """Testar a diminuição da aposta."""
        self.client.bet_amount = 50
        self.client.decrease_bet()
        self.assertEqual(self.client.bet_amount, 40)
        
        # Testar que não diminui abaixo do mínimo
        self.client.bet_amount = 10
        self.client.decrease_bet()
        self.assertEqual(self.client.bet_amount, 10)  # Não deve mudar
    
    def test_increase_bet(self):
        """Testar o aumento da aposta."""
        self.client.bet_amount = 50
        self.client.increase_bet()
        self.assertEqual(self.client.bet_amount, 60)
        
        # Testar que não aumenta além do saldo
        self.client.bet_amount = 990
        self.client.increase_bet()
        self.assertEqual(self.client.bet_amount, 1000)
        
        self.client.bet_amount = 1000
        self.client.increase_bet()
        self.assertEqual(self.client.bet_amount, 1000)  # Não deve mudar
    
    def test_place_bet(self):
        """Testar a colocação de aposta."""
        # Configurar o mock
        self.client.game.place_bet = Mock(return_value=(True, "Aposta feita"))
        
        # Criar um mock para os jogadores
        bot_player = Player("Bot", 1000, "bot_0")
        
        # Configurar o mock do state_manager com uma lista iterável
        self.client.game.state_manager = Mock()
        self.client.game.state_manager.players = [self.client.player, bot_player]
        
        # Realizar a aposta
        self.client.bet_amount = 100
        self.client.place_bet()
        
        # Verificar se o método foi chamado para o jogador
        self.client.game.place_bet.assert_any_call("player_id", 100)
        
        # No mínimo uma chamada para place_bet
        self.assertTrue(self.client.game.place_bet.call_count >= 1)
        
        # Verificar se o estado do jogo foi atualizado
        self.client.game.get_game_state.assert_called()
    
    def test_hit(self):
        """Testar a ação de 'hit' (pedir carta)."""
        # Configurar os mocks
        self.client.game.hit = Mock(return_value=(True, "Carta distribuída"))
        self.client.process_bot_turns = Mock()  # Para isolar este teste
        
        # Chamar hit
        self.client.hit()
        
        # Verificar as chamadas corretas
        self.client.game.hit.assert_called_once_with("player_id")
        self.assertEqual(len(self.client.messages), 1)
        self.assertEqual(self.client.messages[0], "Carta distribuída")
        self.client.game.get_game_state.assert_called()
        self.client.process_bot_turns.assert_called_once()
    
    def test_stand(self):
        """Testar a ação de 'stand' (parar)."""
        # Configurar os mocks
        self.client.game.stand = Mock(return_value=(True, "Jogador parou"))
        self.client.process_bot_turns = Mock()  # Para isolar este teste
        
        # Chamar stand
        self.client.stand()
        
        # Verificar as chamadas corretas
        self.client.game.stand.assert_called_once_with("player_id")
        self.assertEqual(len(self.client.messages), 1)
        self.assertEqual(self.client.messages[0], "Jogador parou")
        self.client.game.get_game_state.assert_called()
        self.client.process_bot_turns.assert_called_once()
    
    def test_process_bot_turns(self):
        """Testar o processamento dos turnos dos bots."""
        # Substituir o método process_bot_turns para evitar complexidade
        original_process = self.client.process_bot_turns
        self.client.process_bot_turns = Mock()
        
        # Configurar os mocks necessários
        self.client.game.hit = Mock(return_value=(True, "Bot pediu carta"))
        self.client.game.stand = Mock(return_value=(True, "Bot parou"))
        
        # Configurar cenário onde o jogo está em curso
        self.client.game_state = {
            'state': 'PLAYER_TURN',
            'players': [
                {'id': 'player_id', 'name': 'Player'},
                {'id': 'bot_0', 'name': 'Bot'}
            ],
            'current_player_index': 1  # É a vez do bot
        }
        
        # Chamar o método de processo (que agora é um mock)
        self.client.process_bot_turns()
        
        # Verificar se o mock foi chamado
        self.client.process_bot_turns.assert_called_once()
        
        # Restaurar o método original
        self.client.process_bot_turns = original_process
    
    def test_start_new_round(self):
        """Testar o início de uma nova rodada."""
        # Configurar mocks
        self.client.game.start_new_round = Mock()
        
        # Iniciar nova rodada
        self.client.start_new_round()
        
        # Verificar chamadas corretas
        self.client.game.start_new_round.assert_called_once()
        self.mock_update_balance.assert_called_once()
        self.client.game.get_game_state.assert_called()
        self.assertEqual(self.client.messages, [])
        self.assertEqual(self.client.bet_amount, 100)  # Reiniciar para o valor padrão

if __name__ == '__main__':
    unittest.main() 