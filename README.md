# Blackjack - Cliente em Python com Pygame

![Blackjack](https://img.shields.io/badge/Blackjack-Client-green)
![Python](https://img.shields.io/badge/Python-3.x-blue)
![Pygame](https://img.shields.io/badge/Pygame-2.x-yellow)

Um jogo de Blackjack em Python utilizando Pygame para a interface gráfica. Este cliente permite jogar Blackjack sozinho contra bots ou em modo multiplayer.

## Recursos Principais

- **Interface Gráfica Atraente**: Design visualmente agradável com elementos interativos.
- **Modo Solo com Bots**: Jogue contra 1-3 bots com comportamento adaptado.
- **Controles Intuitivos**: Apostas, Hit, Stand e outras ações de jogo.
- **Efeitos Visuais**: Animações, sombras e efeitos de hover para melhor experiência.

## Estrutura do Projeto

A arquitetura do projeto segue princípios de separação de responsabilidades e foi refatorada para melhorar a manutenibilidade e testabilidade:

```
client/
├── game_client.py     # Cliente principal do jogo
├── game_interface.py  # Implementação da interface do jogo
├── game_ui.py         # Componentes de UI reutilizáveis
├── ui_manager.py      # Gerenciador de UI centralizado
├── run_tests.py       # Script para executar testes de regressão
├── tests/             # Testes automatizados
│   ├── __init__.py
│   ├── test_game_logic.py    # Testes da lógica do jogo
│   ├── test_ui_manager.py    # Testes dos componentes de UI
│   └── test_integration.py   # Testes de integração
└── assets/            # Imagens, sons e outros recursos
```

## Melhorias Implementadas

### 1. Refatoração da Arquitetura

A base de código foi refatorada para seguir uma arquitetura mais modular:

- **Separação de Responsabilidades**: Interface de usuário separada da lógica de jogo
- **Reusabilidade**: Componentes reutilizáveis para diferentes telas
- **Manutenibilidade**: Código melhor organizado e documentado
- **Testabilidade**: Estrutura que facilita testes automatizados

### 2. Melhorias Visuais

- **Tela de Seleção de Bots**: Interface aprimorada com botões interativos e efeitos visuais
- **Interface de Jogo**: Mesa com visual realista, painéis informativos e controles responsivos
- **Efeitos de Hover**: Feedback visual ao passar o mouse sobre elementos interativos
- **Sombras e Gradientes**: Elementos visuais para melhorar a profundidade e legibilidade

### 3. Testes Automatizados

Implementação de uma suíte de testes completa para garantir a qualidade do código:

- **Testes de Unidade**: Validam componentes individuais do sistema
- **Testes de Integração**: Verificam a interação entre diferentes partes
- **Script de Execução**: Ferramenta prática para executar todos os testes

## Configuração

### Requisitos

- Python 3.x
- Pygame 2.x
- Colorama (para saída colorida nos testes)

### Instalação

```bash
# Clone o repositório
git clone https://github.com/seu-usuario/blackjack.git
cd blackjack

# Instale as dependências
pip install pygame colorama
```

## Execução

```bash
# Execute o jogo
cd client
python game_client.py
```

## Testes

O projeto inclui testes automatizados para garantir a qualidade do código:

```bash
# Execute todos os testes
python client/run_tests.py

# Execute apenas testes específicos
python client/run_tests.py -t ui        # Testes de interface
python client/run_tests.py -t game      # Testes de lógica de jogo
python client/run_tests.py -t integration  # Testes de integração

# Modo verbose para mais detalhes
python client/run_tests.py -v
```

## Contribuições

Contribuições são bem-vindas! Para contribuir:

1. Fork este repositório
2. Crie sua branch de feature (`git checkout -b feature/nova-funcionalidade`)
3. Faça commit das suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

Este projeto está licenciado sob a [Licença MIT](LICENSE).