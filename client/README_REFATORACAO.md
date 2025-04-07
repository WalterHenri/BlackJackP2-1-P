# Refatoração do BlackJack P2P

## Mudanças Realizadas

Esta refatoração separou a lógica do jogo da interface do usuário, seguindo os princípios de separação de responsabilidades.

### 1. Criação do `UIManager`

Criamos um novo arquivo `ui_manager.py` que contém a classe `UIManager`, responsável por toda a renderização e elementos visuais do jogo. Esta classe:

- Implementa todos os métodos de renderização que antes estavam na classe `BlackjackClient`
- Gerencia fontes, cores e estilos visuais
- Cria e posiciona elementos da interface, como botões, mensagens e elementos visuais do jogo
- Retorna informações sobre interações, como retângulos de botões para detecção de cliques

### 2. Atualização da classe `BlackjackClient`

A classe `BlackjackClient` agora:

- Mantém apenas a lógica do jogo (estado, apostas, cartas, jogadores)
- Coordena o fluxo do jogo e gerencia as regras de negócio
- Utiliza o `UIManager` para renderizar a interface
- Interpreta as ações do usuário com base nos elementos de interface fornecidos pelo `UIManager`

### 3. Fluxo de Trabalho

O novo fluxo de trabalho é:

1. `BlackjackClient` mantém o estado do jogo e a lógica
2. Quando é necessário renderizar, `BlackjackClient` chama métodos do `UIManager`
3. O `UIManager` renderiza a interface e retorna referências aos elementos interativos
4. `BlackjackClient` usa essas referências para interpretar os eventos do usuário
5. Com base nos eventos, `BlackjackClient` atualiza o estado do jogo

## Benefícios da Refatoração

- **Separação de responsabilidades**: Código mais organizado e fácil de manter
- **Facilidade de modificação**: Alterar a interface não afeta a lógica do jogo e vice-versa
- **Melhor testabilidade**: Cada componente pode ser testado isoladamente
- **Reutilização de código**: Componentes de interface podem ser reutilizados em diferentes partes do jogo

## Modo Solo

O foco da refatoração foi o modo solo (offline) do jogo, permitindo jogar contra bots. A separação da interface da lógica do jogo facilita futuras expansões e melhorias no modo multiplayer, caso necessário. 