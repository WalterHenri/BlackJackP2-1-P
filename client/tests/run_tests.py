#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def run_tests():
    """Executar todos os testes de regressão."""
    # Descobrir todos os testes no diretório atual
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(os.path.dirname(os.path.abspath(__file__)), pattern="test_*.py")
    
    # Criar um runner e executar os testes
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Retornar um código de saída adequado (0 para sucesso, 1 para falha)
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    print("Executando testes de regressão...")
    result = run_tests()
    
    if result == 0:
        print("\n✅ Todos os testes passaram!")
    else:
        print("\n❌ Falha nos testes!")
        
    sys.exit(result) 