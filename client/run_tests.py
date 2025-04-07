#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
import argparse
from colorama import init, Fore, Style

# Inicializa o colorama para colorir a saída no terminal
init()

def run_tests(test_type=None):
    """Executa os testes de regressão e retorna sucesso (0) se todos passarem ou falha (1) caso contrário."""
    
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    print(f"{Fore.CYAN}  Testes de Regressão - Blackjack    {Style.RESET_ALL}")
    print(f"{Fore.CYAN}======================================{Style.RESET_ALL}")
    
    # Diretório atual onde este script está localizado
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Adiciona o diretório pai ao path para que os imports funcionem
    parent_dir = os.path.dirname(current_dir)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    # Define o tipo de teste a ser executado
    if test_type == 'ui':
        print(f"{Fore.YELLOW}Executando testes de interface...{Style.RESET_ALL}")
        test_suite = unittest.defaultTestLoader.discover(os.path.join(current_dir, 'tests'), pattern='test_ui_manager.py')
    elif test_type == 'game':
        print(f"{Fore.YELLOW}Executando testes de lógica de jogo...{Style.RESET_ALL}")
        test_suite = unittest.defaultTestLoader.discover(os.path.join(current_dir, 'tests'), pattern='test_game_logic.py')
    elif test_type == 'integration':
        print(f"{Fore.YELLOW}Executando testes de integração...{Style.RESET_ALL}")
        test_suite = unittest.defaultTestLoader.discover(os.path.join(current_dir, 'tests'), pattern='test_integration.py')
    else:
        print(f"{Fore.YELLOW}Executando todos os testes...{Style.RESET_ALL}")
        test_suite = unittest.defaultTestLoader.discover(os.path.join(current_dir, 'tests'), pattern='test_*.py')
    
    # Configura o runner para usar o TestResult para capturar os resultados
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Resultado dos testes
    if result.wasSuccessful():
        print(f"\n{Fore.GREEN}✅ Todos os testes passaram!{Style.RESET_ALL}")
        return 0
    else:
        print(f"\n{Fore.RED}❌ Falha nos testes!{Style.RESET_ALL}")
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Executa testes de regressão para o jogo Blackjack.')
    parser.add_argument('-t', '--type', choices=['ui', 'game', 'integration', 'all'], 
                        default='all', help='Tipo de teste a executar (ui, game, integration, all)')
    parser.add_argument('-v', '--verbose', action='store_true', 
                        help='Exibe informações detalhadas durante a execução dos testes')
    
    args = parser.parse_args()
    
    # Configura o nível de verbosidade
    if args.verbose:
        sys.argv.append('-v')
    
    test_type = None if args.type == 'all' else args.type
    sys.exit(run_tests(test_type)) 