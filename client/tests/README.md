# Testes do Cliente Blackjack

Este diretório contém os testes automatizados para o cliente Blackjack. Os testes foram implementados usando o framework `unittest` do Python e estão organizados em diferentes categorias para facilitar a manutenção e execução.

## Estrutura dos Testes

```
tests/
├── __init__.py                # Arquivo que define este diretório como um pacote Python
├── README.md                  # Este arquivo
├── test_game_logic.py         # Testes da lógica do jogo
├── test_ui_manager.py         # Testes dos componentes de UI
└── test_integration.py        # Testes de integração
```

## Categorias de Testes

### 1. Testes de Lógica de Jogo (`test_game_logic.py`)

Testes unitários que validam a lógica do jogo implementada no cliente:

- **Inicialização**: Testa se o cliente é inicializado corretamente
- **Apostas**: Testa as funções de aumentar, diminuir e confirmar apostas
- **Ações do Jogo**: Testa as ações de hit (pedir carta) e stand (parar)
- **Processamento de Turnos**: Testa o processamento dos turnos dos bots
- **Início de Jogo**: Testa as funções de iniciar jogo solo e novas rodadas

### 2. Testes de Interface (`test_ui_manager.py`)

Testes unitários que validam os componentes de interface do usuário:

- **Inicialização**: Testa se o UIManager é inicializado corretamente
- **Renderização de Telas**: Testa a renderização das diferentes telas do jogo
- **Renderização de Componentes**: Testa a renderização de elementos como mesa, mãos e controles
- **Manipulação de Eventos**: Testa a resposta a eventos do usuário

### 3. Testes de Integração (`test_integration.py`)

Testes que validam a interação entre os diferentes componentes do sistema:

- **Interação Cliente-UI**: Testa a comunicação entre o cliente e o gerenciador de UI
- **Processamento de Eventos**: Testa o fluxo completo de eventos do usuário
- **Atualização de Estado**: Testa as atualizações de estado do jogo

## Executando os Testes

Os testes podem ser executados através do script `run_tests.py` na pasta cliente:

```bash
# Executar todos os testes
python client/run_tests.py

# Executar apenas testes de interface
python client/run_tests.py -t ui

# Executar apenas testes de lógica de jogo
python client/run_tests.py -t game

# Executar apenas testes de integração
python client/run_tests.py -t integration

# Modo verbose para mais detalhes
python client/run_tests.py -v
```

## Adicionando Novos Testes

Para adicionar novos testes:

1. Identifique a categoria apropriada (lógica, interface ou integração)
2. Adicione métodos de teste à classe correspondente seguindo a convenção de nomenclatura (`test_nome_do_teste`)
3. Certifique-se de que os novos testes são independentes e isolados
4. Execute os testes para verificar se funcionam corretamente

## Manutenção dos Testes

Os testes devem ser atualizados sempre que houver alterações significativas na base de código. Isso inclui:

- Atualizar asserções quando o comportamento esperado mudar
- Adicionar novos testes para novas funcionalidades
- Remover ou modificar testes obsoletos
- Manter os mocks atualizados quando as interfaces mudarem 