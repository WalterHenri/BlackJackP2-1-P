using Server.Models; // Ainda pode precisar de GameRoom e outros
using System.Net.WebSockets;
using System.Text;
using System.Text.Json; // Para serializar/desserializar JSON
using Microsoft.Extensions.Logging;
using System.Collections.Concurrent; // Para ConcurrentDictionary
using System.Threading;
using System.Threading.Tasks;
using System.Linq;
using System; // Para Random, Math
using System.Collections.Generic; // Para List<>

namespace Server.Services;

#region Game Logic Classes (Idealmente em Models/)

public enum CardSuit { Hearts, Diamonds, Clubs, Spades }
public enum CardRank { Two, Three, Four, Five, Six, Seven, Eight, Nine, Ten, Jack, Queen, King, Ace }
public enum PlayerStatus { Waiting, BetPlaced, Playing, Standing, Blackjack, Busted }
public enum GameState { WaitingForPlayers, Betting, PlayerTurn, DealerTurn, GameOver, Any }

public class Card
{
    public CardSuit Suit { get; }
    public CardRank Rank { get; }
    public string Display => GetDisplayString();
    public int Value => GetCardValue(Rank); // Usar método estático

    public Card(CardSuit suit, CardRank rank)
    {
        Suit = suit;
        Rank = rank;
    }

    private string GetDisplayString()
    {
        string rankStr;
        switch (Rank)
        {
            case CardRank.Jack: rankStr = "J"; break;
            case CardRank.Queen: rankStr = "Q"; break;
            case CardRank.King: rankStr = "K"; break;
            case CardRank.Ace: rankStr = "A"; break;
            default: rankStr = ((int)Rank + 2).ToString(); break; // Two is 0, so +2
        }
        char suitChar = Suit switch
        {
            CardSuit.Hearts => '♥',
            CardSuit.Diamonds => '♦',
            CardSuit.Clubs => '♣',
            CardSuit.Spades => '♠',
            _ => '?'
        };
        return $"{rankStr}{suitChar}";
    }

    // Método estático para obter valor da carta
    public static int GetCardValue(CardRank rank)
    {
        switch (rank)
        {
            case CardRank.Jack:
            case CardRank.Queen:
            case CardRank.King:
                return 10;
            case CardRank.Ace:
                return 11; // Valor inicial do Ás
            default:
                return (int)rank + 2; // Two is 0 -> value 2, Three is 1 -> value 3, etc.
        }
    }

    // Formato para enviar ao cliente
    public object ToClientFormat()
    {
        string rankStr = Rank switch
        {
             CardRank.Jack => "J",
             CardRank.Queen => "Q",
             CardRank.King => "K",
             CardRank.Ace => "A",
             _ => ((int)Rank + 2).ToString()
        };
        return new { suit = Suit.ToString(), value = rankStr, display = Display }; // Adiciona display
    }
}

public class Deck
{
    // Inicializar na declaração para resolver CS8618
    private List<Card> _cards = new List<Card>(); 
    private Random _random = new Random();

    public Deck()
    {
        InitializeDeck(); // Agora só popula a lista existente
        Shuffle();
    }

    private void InitializeDeck()
    {
        _cards.Clear(); // Limpa a lista em vez de criar uma nova
        foreach (CardSuit suit in Enum.GetValues(typeof(CardSuit)))
        {
            foreach (CardRank rank in Enum.GetValues(typeof(CardRank)))
            {
                _cards.Add(new Card(suit, rank));
            }
        }
    }

    public void Shuffle()
    {
        // Fisher-Yates shuffle
        for (int n = _cards.Count - 1; n > 0; --n)
        {
            int k = _random.Next(n + 1);
            Card temp = _cards[n];
            _cards[n] = _cards[k];
            _cards[k] = temp;
        }
    }

    public Card Deal()
    {
        if (_cards.Count == 0) throw new InvalidOperationException("Deck is empty.");
        Card card = _cards[_cards.Count - 1];
        _cards.RemoveAt(_cards.Count - 1);
        return card;
    }
}

public class PlayerState
{
    public string PlayerId { get; }
    public string Name { get; set; }
    public int Balance { get; private set; }
    public int CurrentBet { get; private set; }
    public List<Card> Hand { get; private set; }
    public int HandValue { get; private set; }
    public bool IsBusted => HandValue > 21;
    public PlayerStatus Status { get; set; }

    public PlayerState(string playerId, string name, int initialBalance)
    {
        PlayerId = playerId;
        Name = name;
        Balance = initialBalance;
        Hand = new List<Card>();
        ResetForNewRound();
    }

    public void ResetForNewRound()
    {
        Hand.Clear();
        HandValue = 0;
        CurrentBet = 0;
        Status = PlayerStatus.Waiting;
    }

    public void PlaceBet(int amount)
    {
        if (amount <= 0 || amount > Balance || Status != PlayerStatus.Waiting)
        {
            return;
        }
        CurrentBet = amount;
        Status = PlayerStatus.BetPlaced;
    }

    public void AddCard(Card card)
    {
        Hand.Add(card);
        RecalculateHandValue();
    }

    private void RecalculateHandValue()
    {
        HandValue = 0;
        int aceCount = 0;
        foreach (var card in Hand)
        {
            HandValue += Card.GetCardValue(card.Rank);
            if (card.Rank == CardRank.Ace) aceCount++;
        }
        while (HandValue > 21 && aceCount > 0)
        {
            HandValue -= 10;
            aceCount--;
        }
    }

    public void UpdateBalance(int amount)
    {
        Balance += amount;
    }

    public object ToClientFormat()
    {
        return new
        {
            playerId = PlayerId,
            name = Name,
            balance = Balance,
            currentBet = CurrentBet,
            hand = Hand.Select(c => c.ToClientFormat()).ToList(),
            handValue = HandValue,
            isBusted = IsBusted,
            status = Status.ToString()
        };
    }
}

public class BlackjackGame
{
    public string RoomId { get; }
    private Deck _deck;
    public List<PlayerState> Players { get; private set; }
    public List<Card> DealerHand { get; private set; }
    public int DealerHandValue { get; private set; }
    public bool DealerIsBusted { get; private set; }
    public GameState CurrentState { get; private set; }
    public int CurrentPlayerIndex { get; private set; }
    public List<string> Messages { get; private set; }

    private const int DEALER_STANDS_ON = 17;
    private const decimal BLACKJACK_PAYOUT_RATIO = 3m / 2m; // 3:2 payout

    public BlackjackGame(string roomId, List<(string id, string name)> initialPlayers, int initialBalance = 1000)
    {
        RoomId = roomId;
        _deck = new Deck();
        Players = initialPlayers.Select(p => new PlayerState(p.id, p.name, initialBalance)).ToList();
        DealerHand = new List<Card>();
        Messages = new List<string>();
        StartNewRound();
    }

    public void StartNewRound()
    {
        CurrentState = GameState.Betting;
        CurrentPlayerIndex = -1;
        Messages.Clear();
        Messages.Add("New round started! Place your bets.");
        DealerHand.Clear();
        DealerHandValue = 0;
        DealerIsBusted = false;
        foreach (var player in Players) player.ResetForNewRound();
        _deck = new Deck();
        _deck.Shuffle();
    }

    public bool PlaceBet(string playerId, int amount)
    {
        var player = Players.FirstOrDefault(p => p.PlayerId == playerId);
        if (player == null || CurrentState != GameState.Betting || player.Status != PlayerStatus.Waiting || amount <= 0 || player.Balance < amount)
        {
            return false;
        }
        player.PlaceBet(amount);
        Messages.Add($"{player.Name} placed a bet of {amount}.");
        bool allReady = Players.All(p => p.Status == PlayerStatus.BetPlaced || p.Balance == 0);
        if (allReady && Players.Any(p => p.Status == PlayerStatus.BetPlaced))
        {
            DealInitialCards();
        }
        return true;
    }

    public void DealInitialCards()
    {
        if (CurrentState != GameState.Betting)
        { 
            Messages.Add("Error: Cannot deal cards now."); 
            return; 
        }

        Messages.Add("Dealing initial cards...");
        foreach (var player in Players.Where(p => p.Status == PlayerStatus.BetPlaced))
        {
            player.AddCard(_deck.Deal());
            player.AddCard(_deck.Deal());
            player.Status = PlayerStatus.Playing;
            Messages.Add($"{player.Name} received two cards. Hand value: {player.HandValue}.");
            if (player.HandValue == 21)
            {
                player.Status = PlayerStatus.Blackjack;
                Messages.Add($"{player.Name} has Blackjack!");
            }
        }

        DealerHand.Add(_deck.Deal());
        DealerHand.Add(_deck.Deal());
        DealerHandValue = CalculateHandValue(DealerHand);
        Messages.Add($"Dealer showing: {DealerHand[0].Display} ({Card.GetCardValue(DealerHand[0].Rank)}). Hand Value: ?");

        bool dealerHasBlackjack = (DealerHandValue == 21);
        if (dealerHasBlackjack)
        {
            Messages.Add($"Dealer reveals second card: {DealerHand[1].Display}. Dealer has Blackjack!");
            DealerHandValue = 21;
            CurrentState = GameState.GameOver;
            DetermineWinners();
        }
        else
        {
            CurrentState = GameState.PlayerTurn;
            if (!AdvancePlayerTurn())
            {
                 PlayDealerTurn();
            }
            else
            {
                 Messages.Add($"It's {Players[CurrentPlayerIndex].Name}'s turn.");
            }
        }
    }

    private bool AdvancePlayerTurn()
    {
        if (CurrentState != GameState.PlayerTurn) return false;
        
        CurrentPlayerIndex++;
        while (CurrentPlayerIndex < Players.Count)
        {
            var currentPlayer = Players[CurrentPlayerIndex];
            if (currentPlayer.Status == PlayerStatus.Playing)
            {
                return true;
            }
            CurrentPlayerIndex++;
        }
        return false;
    }

    public bool Hit(string playerId)
    {
        var player = Players.FirstOrDefault(p => p.PlayerId == playerId);
        if (player == null || CurrentState != GameState.PlayerTurn || player.Status != PlayerStatus.Playing || CurrentPlayerIndex < 0 || Players[CurrentPlayerIndex] != player)
        {
            Messages.Add("Error: Cannot Hit now.");
            return false;
        }

        Card dealtCard = _deck.Deal();
        player.AddCard(dealtCard);
        Messages.Add($"{player.Name} hits and receives {dealtCard.Display}. New hand value: {player.HandValue}.");

        if (player.IsBusted)
        {
            player.Status = PlayerStatus.Busted;
            Messages.Add($"{player.Name} busted!");
            if (!AdvancePlayerTurn())
            {
                PlayDealerTurn();
            }
            else
            {
                 Messages.Add($"It's {Players[CurrentPlayerIndex].Name}'s turn.");
            }
        }
        return true;
    }

    public bool Stand(string playerId)
    {
        var player = Players.FirstOrDefault(p => p.PlayerId == playerId);
        if (player == null || CurrentState != GameState.PlayerTurn || player.Status != PlayerStatus.Playing || CurrentPlayerIndex < 0 || Players[CurrentPlayerIndex] != player)
        {
            Messages.Add("Error: Cannot Stand now.");
            return false;
        }

        player.Status = PlayerStatus.Standing;
        Messages.Add($"{player.Name} stands with {player.HandValue}.");

        if (!AdvancePlayerTurn())
        { 
            PlayDealerTurn();
        }
         else
         {
             Messages.Add($"It's {Players[CurrentPlayerIndex].Name}'s turn.");
         }
        return true;
    }

    public void PlayDealerTurn()
    {
        if (CurrentState == GameState.GameOver) return;
        CurrentState = GameState.DealerTurn;
        CurrentPlayerIndex = -1;
        Messages.Add($"Dealer's turn. Revealing hidden card: {DealerHand[1].Display}. Dealer hand value: {DealerHandValue}.");

        while (DealerHandValue < DEALER_STANDS_ON)
        {
            Card dealtCard = _deck.Deal();
            DealerHand.Add(dealtCard);
            DealerHandValue = CalculateHandValue(DealerHand);
            Messages.Add($"Dealer hits and receives {dealtCard.Display}. New hand value: {DealerHandValue}.");
            if (DealerHandValue > 21)
            {
                DealerIsBusted = true;
                Messages.Add("Dealer busted!");
                break;
            }
        }

        if (!DealerIsBusted)
        {
            Messages.Add($"Dealer stands with {DealerHandValue}.");
        }

        CurrentState = GameState.GameOver;
        DetermineWinners();
    }

    public void DetermineWinners()
    {
        if (CurrentState != GameState.GameOver)
        { 
            Messages.Add("Error: Cannot determine winners yet."); 
            return; 
        }

        Messages.Add("--- Round Over --- Determining Winners ---");
        Messages.Add($"Dealer has: {DealerHandValue}{(DealerIsBusted ? " (Busted)" : "")}.");

        foreach (var player in Players.Where(p => p.Status != PlayerStatus.Waiting))
        {
            string resultMsg = $"{player.Name} ({player.HandValue})";
            int winnings = 0;

            if (player.Status == PlayerStatus.Busted)
            {
                resultMsg += " busted and loses bet.";
                winnings = -player.CurrentBet;
            }
            else if (player.Status == PlayerStatus.Blackjack)
            {
                if (DealerHandValue == 21 && DealerHand.Count == 2)
                { 
                    resultMsg += " pushes (both Blackjack).";
                    winnings = 0;
                }
                else 
                { 
                    resultMsg += " has Blackjack and wins!";
                    winnings = (int)(player.CurrentBet * BLACKJACK_PAYOUT_RATIO);
                }
            }
            else if (DealerIsBusted)
            { 
                resultMsg += " wins (Dealer busted).";
                winnings = player.CurrentBet;
            }
            else if (player.HandValue > DealerHandValue)
            { 
                resultMsg += " wins.";
                winnings = player.CurrentBet;
            }
            else if (player.HandValue == DealerHandValue)
            { 
                resultMsg += " pushes (tie).";
                winnings = 0;
            }
            else
            { 
                resultMsg += " loses.";
                winnings = -player.CurrentBet;
            }
            
            player.UpdateBalance(winnings);
            resultMsg += $" Bet: {player.CurrentBet}, Winnings: {winnings}, New Balance: {player.Balance}.";
            Messages.Add(resultMsg);
        }
         Messages.Add("--- Ready for New Round ---");
    }

    private int CalculateHandValue(List<Card> hand)
    {
        int value = 0;
        int aceCount = 0;
        foreach (var card in hand)
        {
            value += Card.GetCardValue(card.Rank);
            if (card.Rank == CardRank.Ace) aceCount++;
        }
        while (value > 21 && aceCount > 0)
        {
            value -= 10;
            aceCount--;
        }
        return value;
    }

    public object GetGameState()
    {
        List<object>? dealerClientHand = null;
        int? dealerClientValue = null;

        if (CurrentState == GameState.Betting || CurrentState == GameState.PlayerTurn)
        {
            if (DealerHand.Count > 0)
            {
                dealerClientHand = new List<object> { DealerHand[0].ToClientFormat(), new { suit = "Hidden", value = "?", display="?"} };
                dealerClientValue = Card.GetCardValue(DealerHand[0].Rank);
            }
            else
            {
                dealerClientHand = new List<object>();
                dealerClientValue = 0;
            }
        }
        else
        {
            dealerClientHand = DealerHand.Select(c => c.ToClientFormat()).ToList();
            dealerClientValue = DealerHandValue;
        }

        return new
        {
            roomId = RoomId,
            state = CurrentState.ToString(),
            players = Players.Select(p => p.ToClientFormat()).ToList(),
            dealerHand = dealerClientHand,
            dealerValue = dealerClientValue,
            dealerIsBusted = DealerIsBusted,
            currentPlayerIndex = CurrentPlayerIndex,
            messages = new List<string>(Messages)
        };
    }
}

#endregion

// Classe adaptada de BlackJackServer para usar WebSockets
public class WebSocketManager
{
    // Dicionário para armazenar conexões WebSocket ativas (ID -> WebSocket)
    private readonly ConcurrentDictionary<string, WebSocket> _sockets = new ConcurrentDictionary<string, WebSocket>();
    // Dicionário para associar ID de conexão a um ID de jogador (opcional, mas útil)
    private readonly ConcurrentDictionary<string, string> _connectionIdToPlayerId = new ConcurrentDictionary<string, string>();
    // Dicionário para associar ID de jogador a um nome (simples por enquanto)
    private readonly ConcurrentDictionary<string, string> _playerIdToName = new ConcurrentDictionary<string, string>();
    // NOVO: Dicionário para associar ID de jogador ao ID da sala em que está
    private readonly ConcurrentDictionary<string, string> _playerIdToRoomId = new ConcurrentDictionary<string, string>();
    // NOVO: Dicionário para associar ID de jogador ao ID da conexão atual
    private readonly ConcurrentDictionary<string, string> _playerIdToConnectionId = new ConcurrentDictionary<string, string>();
    // NOVO: Dicionário para armazenar instâncias de jogo ativas por sala
    private readonly ConcurrentDictionary<string, BlackjackGame> _games = new ConcurrentDictionary<string, BlackjackGame>();

    // Manter a lógica das salas (talvez precise adaptar GameRoom)
    private readonly ConcurrentDictionary<string, GameRoom> _rooms = new ConcurrentDictionary<string, GameRoom>();
    private readonly ILogger<WebSocketManager> _logger;

    // Usando ILogger<WebSocketManager> agora
    public WebSocketManager(ILogger<WebSocketManager> logger)
    {
        _logger = logger;
        _logger.LogInformation("WebSocket Manager Initialized.");
        // Iniciar tarefa de limpeza de salas inativas (opcional, pode ser reativada)
        // _ = Task.Run(async () => await CleanupInactiveRoomsAsync(CancellationToken.None));
    }

    // Método chamado pelo Startup para lidar com uma nova conexão WebSocket
    public async Task HandleWebSocketAsync(WebSocket webSocket, CancellationToken cancellationToken)
    {
        string connectionId = Guid.NewGuid().ToString(); // Gera um ID único para a conexão
        _sockets.TryAdd(connectionId, webSocket);
        _logger.LogInformation($"WebSocket connected: {connectionId}");

        try
        {
            // Loop para receber mensagens do cliente
            while (webSocket.State == WebSocketState.Open && !cancellationToken.IsCancellationRequested)
            {
                string? messageJson = await ReceiveMessageAsync(webSocket, cancellationToken);
                if (messageJson != null)
                {
                    await ProcessMessageAsync(connectionId, messageJson);
                }
                else if (webSocket.State != WebSocketState.Open)
                {
                    // Sai do loop se o estado mudou durante ReceiveMessageAsync
                    break;
                }
                // Pequena pausa para não sobrecarregar a CPU se não houver mensagens
                await Task.Delay(10, cancellationToken);
            }
        }
        catch (WebSocketException ex) when (ex.WebSocketErrorCode == WebSocketError.ConnectionClosedPrematurely || ex.WebSocketErrorCode == WebSocketError.InvalidState)
        {
            _logger.LogWarning($"WebSocket {connectionId} closed prematurely: {ex.Message}");
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation($"WebSocket {connectionId} operation canceled (client disconnected).");
        }
        catch (Exception ex)
        {
            _logger.LogError($"Error handling WebSocket {connectionId}: {ex.GetType().Name} - {ex.Message}");
            // Tentar fechar o socket graciosamente em caso de erro não esperado
            if (webSocket.State == WebSocketState.Open || webSocket.State == WebSocketState.CloseReceived || webSocket.State == WebSocketState.CloseSent)
            {
                 try
                 {
                      await webSocket.CloseAsync(WebSocketCloseStatus.InternalServerError, "Server error", CancellationToken.None); // Use CancellationToken.None para garantir o envio
                 }
                 catch (Exception closeEx)
                 {
                      _logger.LogError($"Exception while trying to close socket {connectionId} after error: {closeEx.Message}");
                 }
            }
        }
        finally
        {
            // Limpeza ao desconectar
            await OnDisconnectedAsync(connectionId);
        }
    }

    // Método auxiliar para receber uma mensagem completa do WebSocket
    private async Task<string?> ReceiveMessageAsync(WebSocket webSocket, CancellationToken cancellationToken)
    {
        var buffer = new ArraySegment<byte>(new byte[8192]);
        using (var ms = new MemoryStream())
        {
            WebSocketReceiveResult result;
            do
            {
                // Verifica se o cliente iniciou o fechamento
                if (webSocket.State != WebSocketState.Open)
                {
                    return null; // Sai se o estado não for Open
                }
                try
                {
                    result = await webSocket.ReceiveAsync(buffer, cancellationToken);
                }
                catch (WebSocketException ex) when (ex.WebSocketErrorCode == WebSocketError.ConnectionClosedPrematurely)
                {
                    // Tratamento específico para fechamento prematuro
                    _logger.LogInformation("ReceiveMessageAsync: Connection closed prematurely.");
                    return null;
                }
                catch (OperationCanceledException)
                {
                     _logger.LogInformation("ReceiveMessageAsync: Operation canceled.");
                    return null; // Sai se a operação for cancelada
                }

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    _logger.LogInformation("ReceiveMessageAsync: Received close message.");
                    // Tenta completar o handshake de fechamento
                     if (webSocket.State == WebSocketState.CloseReceived)
                     {
                          // Importante usar CancellationToken.None aqui para garantir que tentamos fechar
                          try
                          {
                                await webSocket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "Client requested closure", CancellationToken.None);
                                _logger.LogInformation("ReceiveMessageAsync: Sent close confirmation.");
                          }
                          catch(Exception closeEx)
                          {
                                _logger.LogError($"Exception during CloseOutputAsync: {closeEx.Message}");
                          }
                     }
                    return null; // Indica que a conexão deve ser fechada
                }
                 if (result.MessageType != WebSocketMessageType.Text)
                 {
                     _logger.LogWarning($"ReceiveMessageAsync: Received non-text message type: {result.MessageType}");
                     continue; // Ignora mensagens não-texto por enquanto
                 }

                 if (buffer.Array == null) // Verificação de nulidade adicionada
                 {
                     _logger.LogWarning("ReceiveMessageAsync: Buffer array is null.");
                     continue;
                 }

                ms.Write(buffer.Array, buffer.Offset, result.Count);

            } while (!result.EndOfMessage && !cancellationToken.IsCancellationRequested);

             if (cancellationToken.IsCancellationRequested)
             {
                  _logger.LogInformation("ReceiveMessageAsync: Cancellation requested during message reception.");
                 return null;
             }

            ms.Seek(0, SeekOrigin.Begin);
            // Usar ReadToEndAsync com CancellationToken se disponível (.NET 6+)
            #if NET6_0_OR_GREATER
                using (var reader = new StreamReader(ms, Encoding.UTF8))
                {
                     // Pass CancellationToken to ReadToEndAsync
                     return await reader.ReadToEndAsync(cancellationToken);
                }
            #else
                using (var reader = new StreamReader(ms, Encoding.UTF8))
                {
                    return await reader.ReadToEndAsync();
                }
            #endif
        }
    }

    // Processa uma mensagem JSON recebida de um cliente
    private async Task ProcessMessageAsync(string connectionId, string messageJson)
    {
        _logger.LogInformation($"[WebSocket {connectionId}] Received JSON: {messageJson}");
        try
        {
            // Usar System.Text.Json para desserializar para um tipo base ou JDocument
            using (JsonDocument document = JsonDocument.Parse(messageJson))
            {
                if (document.RootElement.TryGetProperty("type", out JsonElement typeElement) &&
                    typeElement.ValueKind == JsonValueKind.String)
                {
                    string messageType = typeElement.GetString() ?? "";
                    JsonElement payloadElement = document.RootElement.TryGetProperty("payload", out var p) ? p : default;
                    
                     _logger.LogInformation($"Processing message type {messageType} from {connectionId}");

                    switch (messageType.ToUpper())
                    {
                        case "SET_NAME":
                            await HandleSetNameAsync(connectionId, payloadElement);
                            break;
                        case "LIST_ROOMS":
                            await HandleListRoomsAsync(connectionId);
                            break;
                        case "CREATE_ROOM":
                            await HandleCreateRoomAsync(connectionId, payloadElement);
                            break;
                        case "JOIN_ROOM":
                            await HandleJoinRoomAsync(connectionId, payloadElement);
                            break;
                        case "LEAVE_ROOM":
                            await HandleLeaveRoomAsync(connectionId);
                            break;
                        case "START_GAME":
                            await HandleStartGameAsync(connectionId, payloadElement);
                            break;
                        case "PLACE_BET":
                            await HandlePlaceBetAsync(connectionId, payloadElement);
                            break;
                        case "HIT":
                            await HandleHitAsync(connectionId, payloadElement);
                            break;
                        case "STAND":
                            await HandleStandAsync(connectionId, payloadElement);
                            break;
                        case "NEW_ROUND":
                            await HandleNewRoundAsync(connectionId, payloadElement);
                            break;
                        // Adicionar outros casos: GAME_ACTION, CHAT, etc.
                        default:
                             _logger.LogWarning($"Unknown message type received from {connectionId}: {messageType}");
                            await SendErrorAsync(connectionId, $"Unknown message type: {messageType}");
                            break;
                    }
                }
                 else
                 {
                     _logger.LogWarning($"Invalid message format from {connectionId}: missing 'type' property.");
                     await SendErrorAsync(connectionId, "Invalid message format: 'type' is required.");
                 }
            }
        }
        catch (JsonException jsonEx)
        {
             _logger.LogError($"JSON parsing error from {connectionId}: {jsonEx.Message}");
            await SendErrorAsync(connectionId, "Invalid JSON format.");
        }
        catch (Exception ex)
        {
             _logger.LogError($"Error processing message from {connectionId}: {ex.ToString()}");
            await SendErrorAsync(connectionId, "An internal server error occurred.");
        }
    }

    // --- Handlers específicos para tipos de mensagem --- //

     private Task HandleSetNameAsync(string connectionId, JsonElement payload)
    {
        string? name = null;
        try
        {
             name = payload.TryGetProperty("name", out var n) && n.ValueKind == JsonValueKind.String ? n.GetString() : null;
        } catch (InvalidOperationException) {/* Ignore se payload não for um objeto */}


        if (string.IsNullOrWhiteSpace(name))
        {
            return SendErrorAsync(connectionId, "Name cannot be empty.");
        }

        // Remover mapeamentos antigos se o jogador já existia com outro nome/conexão (opcional)
        string? oldPlayerId = null;
         // Corrigido: Use a variável declarada 'existingPlayerId'
        if (_connectionIdToPlayerId.TryGetValue(connectionId, out string? existingPlayerId) && existingPlayerId != null)
        {
             oldPlayerId = existingPlayerId;
             _playerIdToName.TryRemove(existingPlayerId, out _);
             _playerIdToConnectionId.TryRemove(existingPlayerId, out _);
             // Não remover de _playerIdToRoomId aqui, pois ele pode estar numa sala
        }


        string playerId = Guid.NewGuid().ToString(); // Gera um ID de jogador
        _connectionIdToPlayerId[connectionId] = playerId; // Atualiza ou adiciona
        _playerIdToName[playerId] = name;
        _playerIdToConnectionId[playerId] = connectionId; // Mapeia playerId para connectionId
        _logger.LogInformation($"Connection {connectionId} set name to '{name}' (PlayerID: {playerId}). Previous PlayerID: {oldPlayerId ?? "None"}");

        // Enviar confirmação
        return SendMessageAsync(connectionId, new { type = "NAME_SET", payload = new { playerId = playerId, name = name } });
    }


    private async Task HandleListRoomsAsync(string connectionId)
    {
        _logger.LogInformation($"Handling LIST_ROOMS request from {connectionId}");
        try
        {
            // Adapta o formato de GetAvailableRooms para o cliente
            var availableRooms = _rooms.Values
                .Where(r => !r.IsInProgress) // Mostra todas as salas não iniciadas
                .Select(r => new {
                    id = r.Id,
                    name = r.Name,
                    playerCount = r.Players.Count,
                    hasPassword = !string.IsNullOrEmpty(r.Password),
                    hostName = GetPlayerName(r.HostPlayerId) // Assumindo que GameRoom tem HostPlayerId
                })
                .ToList(); // Materializa a lista

            await SendMessageAsync(connectionId, new { type = "ROOMS_LIST", payload = availableRooms });
        }
        catch (Exception ex)
        {
             _logger.LogError($"Error handling LIST_ROOMS: {ex.Message}");
             await SendErrorAsync(connectionId, "Error retrieving room list.");
        }
    }

    private async Task HandleCreateRoomAsync(string connectionId, JsonElement payload)
    {
         _logger.LogInformation($"Handling CREATE_ROOM request from {connectionId}");

         // Validar se o jogador já tem nome
        if (!_connectionIdToPlayerId.TryGetValue(connectionId, out string? playerId) || playerId == null)
        {
            await SendErrorAsync(connectionId, "Cannot create room: Player name not set.");
            return;
        }

         // Validar se o jogador já está em outra sala
        if (_playerIdToRoomId.ContainsKey(playerId))
        {
             await SendErrorAsync(connectionId, "You are already in a room. Leave it first.");
             return;
        }

        // Extrair dados do payload
         string? roomName = null;
         string? password = null;
         int maxPlayers = 8; // Default

        try {
             roomName = payload.TryGetProperty("roomName", out var rn) && rn.ValueKind == JsonValueKind.String ? rn.GetString() : $"Room_{Guid.NewGuid().ToString().Substring(0, 4)}";
             password = payload.TryGetProperty("password", out var pw) && pw.ValueKind == JsonValueKind.String ? pw.GetString() : null;
             maxPlayers = payload.TryGetProperty("maxPlayers", out var mp) && mp.TryGetInt32(out int mpVal) ? mpVal : 8;
        } catch (InvalidOperationException) {/* Ignore se payload não for objeto */}


        if (string.IsNullOrWhiteSpace(roomName)) roomName = $"Room_{Guid.NewGuid().ToString().Substring(0, 4)}"; // Garante nome não vazio
        if (string.IsNullOrEmpty(password)) password = null; // Normaliza senha vazia para null

        try
        {
            var newRoom = new GameRoom(roomName, maxPlayers, password)
            {
                 HostPlayerId = playerId // Define o criador como host
            };

            if (_rooms.TryAdd(newRoom.Id, newRoom))
            {
                _logger.LogInformation($"Room '{newRoom.Name}' (ID: {newRoom.Id}) created by {GetPlayerName(playerId)} ({playerId}).");

                // Adicionar criador à sala e ao mapeamento player->sala
                if (newRoom.AddPlayer(playerId))
                {
                     _playerIdToRoomId[playerId] = newRoom.Id;
                     _logger.LogInformation($"Player {playerId} added to room {newRoom.Id}.");
                } else {
                     _logger.LogWarning($"Failed to add host {playerId} to newly created room {newRoom.Id}.");
                     // Considerar remover a sala se o host não puder ser adicionado?
                      _rooms.TryRemove(newRoom.Id, out _); // Remove sala se host não pode entrar
                      await SendErrorAsync(connectionId, "Failed to add host to the room after creation.");
                      return;
                }

                // Enviar confirmação ao criador
                await SendMessageAsync(connectionId, new { type = "ROOM_CREATED", payload = new { roomId = newRoom.Id, name = newRoom.Name, hostPlayerId = newRoom.HostPlayerId } });

                // Notificar outros sobre a nova sala (opcional, LIST_ROOMS pode ser suficiente)
                // await BroadcastMessageAsync(new { type = "NEW_ROOM_AVAILABLE", payload = new { id = newRoom.Id, name = newRoom.Name, playerCount = 1, hasPassword = !string.IsNullOrEmpty(newRoom.Password) } }, connectionId);
            }
            else
            {
                _logger.LogError($"Failed to add room {newRoom.Id} to dictionary (ID collision?).");
                await SendErrorAsync(connectionId, "Failed to create room due to a server issue.");
            }
        }
        catch (Exception ex)
        {
             _logger.LogError($"Error creating room: {ex.Message}");
             await SendErrorAsync(connectionId, "Error creating room.");
        }
    }

    private async Task HandleJoinRoomAsync(string connectionId, JsonElement payload)
    {
         _logger.LogInformation($"Handling JOIN_ROOM request from {connectionId}");

        // Validar se o jogador já tem nome
        if (!_connectionIdToPlayerId.TryGetValue(connectionId, out string? playerId) || playerId == null)
        {
            await SendErrorAsync(connectionId, "Cannot join room: Player name not set.");
            return;
        }

         // Validar se o jogador já está em outra sala
         if (_playerIdToRoomId.ContainsKey(playerId))
         {
             string? currentRoomId = FindRoomByPlayerId(playerId); // Re-verifica se sala existe
             if (currentRoomId != null) {
                 await SendErrorAsync(connectionId, $"You are already in room {currentRoomId}. Leave it first.");
                 return;
             } else {
                 // Inconsistência, remove mapeamento antigo
                 _playerIdToRoomId.TryRemove(playerId, out _);
             }
         }

         string? roomId = null;
         string? password = null;
         try {
             roomId = payload.TryGetProperty("roomId", out var r) && r.ValueKind == JsonValueKind.String ? r.GetString() : null;
             password = payload.TryGetProperty("password", out var pw) && pw.ValueKind == JsonValueKind.String ? pw.GetString() : null; // Senha pode ser null
         } catch (InvalidOperationException) {/* Ignore */}

        if (string.IsNullOrEmpty(roomId) || !_rooms.TryGetValue(roomId, out GameRoom? room) || room == null)
        {
            await SendErrorAsync(connectionId, "Room not found.");
            return;
        }

        // Verificar senha
        if (!string.IsNullOrEmpty(room.Password) && room.Password != password)
        {
            await SendErrorAsync(connectionId, "Incorrect password.");
            return;
        }

        // Verificar se pode entrar (vagas, jogo não iniciado)
        if (!room.CanJoin())
        {
            await SendErrorAsync(connectionId, room.IsInProgress ? "Game already in progress." : "Room is full.");
            return;
        }

        // Adicionar jogador à sala
        if (room.AddPlayer(playerId))
        {
            _playerIdToRoomId[playerId] = roomId; // Mapeia jogador para a sala
            _logger.LogInformation($"Player {GetPlayerName(playerId)} ({playerId}) joined room {roomId} ('{room.Name}').");

             // Preparar payload de sucesso
             var playersInRoomInfo = room.Players.Select(pId => new { id = pId, name = GetPlayerName(pId) }).ToList();
             var successPayload = new {
                 roomId = room.Id,
                 name = room.Name,
                 hostPlayerId = room.HostPlayerId,
                 players = playersInRoomInfo
             };

            // Enviar confirmação ao jogador que entrou
            await SendMessageAsync(connectionId, new { type = "JOIN_SUCCESS", payload = successPayload });

            // Notificar outros jogadores na sala sobre o novo jogador
            var playerJoinedPayload = new { player = new { id = playerId, name = GetPlayerName(playerId) } };
            // Enviar para todos na sala, EXCETO para quem acabou de entrar
            await BroadcastMessageToRoomAsync(room.Id, new { type = "PLAYER_JOINED", payload = playerJoinedPayload }, excludePlayerId: playerId);
        }
        else
        {
            // Isso não deveria acontecer se CanJoin() passou, mas por segurança...
            await SendErrorAsync(connectionId, "Failed to join room (server error or race condition).");
        }
    }


    private async Task HandleLeaveRoomAsync(string connectionId)
     {
         // Usa o mapeamento reverso se disponível, senão o ID da conexão
         string? leavingPlayerId = null;
         if (!_connectionIdToPlayerId.TryGetValue(connectionId, out leavingPlayerId) || leavingPlayerId == null)
         {
              _logger.LogWarning($"Cannot handle LEAVE_ROOM/disconnect for unknown connection: {connectionId}");
              // Não fazer mais nada se a conexão não é conhecida
              return;
         }

         // Encontra a sala usando o novo mapeamento eficiente
         if (!_playerIdToRoomId.TryRemove(leavingPlayerId, out string? roomId) || roomId == null)
         {
             // Jogador não estava em nenhuma sala (ou já foi removido)
             _logger.LogInformation($"Player {leavingPlayerId} (Conn: {connectionId}) tried to leave, but was not mapped to any room.");
             return; // Sai silenciosamente, pois o estado já está limpo
         }


         _logger.LogInformation($"Handling LEAVE_ROOM for Player {leavingPlayerId} from Room {roomId} - Conn: {connectionId}");

          // Encontra a sala
         if (!_rooms.TryGetValue(roomId, out GameRoom? room) || room == null) {
              _logger.LogWarning($"Player {leavingPlayerId} was mapped to room {roomId}, but room not found in dictionary.");
              return; // Sala não existe mais?
         }


         string playerName = GetPlayerName(leavingPlayerId); // Guarda o nome antes de remover
         bool removed = room.RemovePlayer(leavingPlayerId); // Remove jogador da sala

         if (removed)
         {
             _logger.LogInformation($"Player {playerName} ({leavingPlayerId}) removed from room {roomId} ('{room.Name}').");

             // Notificar outros jogadores na sala
             var playerLeftPayload = new { playerId = leavingPlayerId };
             await BroadcastMessageToRoomAsync(room.Id, new { type = "PLAYER_LEFT", payload = playerLeftPayload }, excludePlayerId: leavingPlayerId); // Notifica todos os outros


             // Lidar com a saída do Host
             bool roomRemoved = false;
             if (room.Players.Count == 0) {
                  _logger.LogInformation($"Room {roomId} ('{room.Name}') is now empty. Removing room.");
                  if (_rooms.TryRemove(roomId, out _)) {
                       roomRemoved = true;
                       // Limpar instância de jogo se existir
                        if (_games.TryRemove(roomId, out BlackjackGame? gameInstance))
                        {
                             _logger.LogInformation($"Removed BlackjackGame instance for cleaned up room {roomId}.");
                             // gameInstance.Dispose(); // Se necessário
                        }
                  } else {
                       _logger.LogWarning($"Failed to remove empty room {roomId} from dictionary.");
                  }
             }
             else if (room.HostPlayerId == leavingPlayerId) // Se o host saiu e a sala não está vazia
             {
                  _logger.LogInformation($"Host {playerName} left room {roomId}. Assigning new host.");
                  room.AssignNewHost(); // Atribui um novo host
                  if (!string.IsNullOrEmpty(room.HostPlayerId))
                  {
                       _logger.LogInformation($"New host for room {roomId} is {GetPlayerName(room.HostPlayerId)} ({room.HostPlayerId}).");
                       // Notificar todos sobre o novo host
                       var newHostPayload = new { hostId = room.HostPlayerId, hostName = GetPlayerName(room.HostPlayerId) };
                       await BroadcastMessageToRoomAsync(room.Id, new { type = "NEW_HOST", payload = newHostPayload });
                  }
                  else
                  {
                       _logger.LogError($"Room {roomId} has players but failed to assign a new host after host left.");
                       // O que fazer aqui? Fechar a sala?
                  }
             }

             // Se a sala foi removida, não há mais nada a fazer aqui
             if(roomRemoved) return;

         }
         else
         {
             // Jogador não estava na lista da sala (inconsistência?)
             _logger.LogWarning($"Player {leavingPlayerId} tried to leave room {roomId}, but was not found in the room's player list.");
             // Não enviar erro, pois o estado desejado (jogador fora da sala) já foi alcançado
         }
     }


    private async Task HandleStartGameAsync(string connectionId, JsonElement payload)
    {
        _logger.LogInformation($"Handling START_GAME request from {connectionId}");
        if (!ValidatePlayerAndRoom(connectionId, payload, out string? playerId, out string? roomId, out GameRoom? room, out _))
        { return; }
         if (playerId == null || roomId == null || room == null) return;
        if (room.HostPlayerId != playerId) { await SendErrorAsync(connectionId, "Only host can start."); return; }
        if (room.IsInProgress || _games.ContainsKey(roomId)) { await SendErrorAsync(connectionId, "Game already in progress."); return; }
        int minPlayers = 1;
        if (room.Players.Count < minPlayers) { await SendErrorAsync(connectionId, $"Need at least {minPlayers} player(s)."); return; }

        _logger.LogInformation($"Host {GetPlayerName(playerId)} ({playerId}) starting game in room {roomId}.");
        room.IsInProgress = true;
        try
        {
             var playerInfos = room.Players.Select(pId => (pId, GetPlayerName(pId))).ToList();
             var game = new BlackjackGame(roomId, playerInfos);
             if (_games.TryAdd(roomId, game))
             {
                  _logger.LogInformation($"BlackjackGame instance created for room {roomId}. Initial state: {game.CurrentState}");
                  await BroadcastGameStateAsync(room, game.GetGameState());
             }
             else { throw new Exception("Failed to store game instance."); }
        }
        catch (Exception ex)
        {
             _logger.LogError($"Exception starting game {roomId}: {ex.Message}");
             room.IsInProgress = false;
             _games.TryRemove(roomId, out _);
             await SendErrorAsync(connectionId, "Server error starting game.");
        }
    }

    // --- Implementação HandlePlaceBetAsync ---
    private async Task HandlePlaceBetAsync(string connectionId, JsonElement payload)
    {
        _logger.LogInformation($"Handling PLACE_BET from {connectionId}");
        // Validação básica: jogador existe, sala existe, jogo existe, estado é Betting
        if (!ValidatePlayerAndGameAction(connectionId, payload, GameState.Betting, out string? playerId, out GameRoom? room, out BlackjackGame? game))
        {
            // Loga o erro dentro de ValidatePlayerAndGameAction
            // await SendErrorAsync(connectionId, "Invalid action or game state for placing bet."); // Opcional, Validate já pode enviar
            return;
        }
        if (playerId == null || room == null || game == null) return; // Checagem extra

        // Extrair valor da aposta do payload
        if (!payload.TryGetProperty("amount", out JsonElement amountElement) || !amountElement.TryGetInt32(out int amount) || amount <= 0)
        {
            _logger.LogWarning($"Invalid or missing bet amount from {playerId} in room {game.RoomId}. Payload: {payload}");
            await SendErrorAsync(connectionId, "Invalid bet amount specified.");
            return;
        }

        // Tentar colocar a aposta usando a lógica do jogo
        if (game.PlaceBet(playerId, amount))
        {
            _logger.LogInformation($"{GetPlayerName(playerId)} placed bet {amount} in room {game.RoomId}.");

            // Verificar se TODOS os jogadores já apostaram
            bool allPlayersBet = game.Players.All(p => p.CurrentBet > 0 || p.Status == PlayerStatus.Waiting); // Assume Waiting se não for apostar
             if (allPlayersBet)
            {
                _logger.LogInformation($"All players have placed bets in room {game.RoomId}. Dealing initial cards.");
                // ***** AQUI ENTRA A LÓGICA PARA DISTRIBUIR AS CARTAS *****
                game.DealInitialCards(); // Mudar estado para PlayerTurn e adicionar msg
                // Idealmente, DealInitialCards faria a distribuição real
                _logger.LogInformation($"Game state changed to {game.CurrentState} in room {game.RoomId}. Current player index: {game.CurrentPlayerIndex}");
            }
            else
            {
                _logger.LogInformation($"Waiting for other players to bet in room {game.RoomId}.");
            }

            // Enviar estado atualizado para todos na sala
            await BroadcastGameStateAsync(room, game.GetGameState());
        }
        else
        {
            // game.PlaceBet retornou false (saldo insuficiente, estado errado, etc.)
            _logger.LogWarning($"Failed to place bet for {playerId} in room {game.RoomId}. Amount: {amount}");
            // Enviar erro específico pode ser útil, mas game.PlaceBet precisaria retornar o motivo
            await SendErrorAsync(connectionId, "Failed to place bet (e.g., insufficient funds or invalid state).");
            // Opcional: Reenviar estado caso a falha não seja óbvia para o cliente
            // await BroadcastGameStateAsync(room, game.GetGameState());
        }
    }

    // --- Handlers Vazios/Placeholders (sem alterações nesta etapa) ---
    private async Task HandleHitAsync(string connectionId, JsonElement payload)
    {
        _logger.LogInformation($"Handling HIT from {connectionId}");
        if (!ValidatePlayerAndGameAction(connectionId, payload, GameState.PlayerTurn, out _, out GameRoom? room, out BlackjackGame? game)) return;
        _logger.LogWarning("HIT logic not implemented in handler.");
        await SendErrorAsync(connectionId, "Hit not implemented yet.");
        if(room != null && game != null) await BroadcastGameStateAsync(room, game.GetGameState());
    }
    private async Task HandleStandAsync(string connectionId, JsonElement payload)
    {
        _logger.LogInformation($"Handling STAND from {connectionId}");
        if (!ValidatePlayerAndGameAction(connectionId, payload, GameState.PlayerTurn, out _, out GameRoom? room, out BlackjackGame? game)) return;
        _logger.LogWarning("STAND logic not implemented in handler.");
        await SendErrorAsync(connectionId, "Stand not implemented yet.");
        if(room != null && game != null) await BroadcastGameStateAsync(room, game.GetGameState());
    }
     private async Task HandleNewRoundAsync(string connectionId, JsonElement payload)
    {
        _logger.LogInformation($"Handling NEW_ROUND request from {connectionId}");
        // Deveria validar estado GameOver ou talvez permitir a qualquer momento se for o host?
        if (!ValidatePlayerAndGameAction(connectionId, payload, GameState.GameOver, out string? playerId, out GameRoom? room, out BlackjackGame? game)) return;
         if (playerId == null || room == null || game == null) return;

        // Verificar se é o host quem pediu nova rodada? (Opcional)
        // if (room.HostPlayerId != playerId) { ... }

        _logger.LogInformation($"Starting new round in room {game.RoomId} as requested by {playerId}.");
        game.StartNewRound();
        await BroadcastGameStateAsync(room, game.GetGameState());
    }

    // --- Métodos Auxiliares (Incluindo validação corrigida) --- //

    // Validação combinada para ações de jogo
    private bool ValidatePlayerAndGameAction(string connectionId, JsonElement payload, GameState requiredState, out string? playerId, out GameRoom? room, out BlackjackGame? game)
    {
        playerId = null;
        room = null;
        game = null;

        // 1. Validar jogador e sala base
        if (!ValidatePlayerAndRoom(connectionId, payload, out playerId, out string? roomId, out room, out _))
        {
            return false; // Erro já logado e possivelmente enviado
        }
        if (playerId == null || roomId == null || room == null) return false; // Defesa extra

        // 2. Encontrar a instância do jogo para a sala
        if (!_games.TryGetValue(roomId, out game) || game == null)
        {
            _logger.LogError($"Game instance not found for room {roomId} when requested by {playerId} ({connectionId}). Action requires active game.");
            SendErrorAsync(connectionId, "No active game found for this room.").Wait(); // Considerar async void pattern com cuidado
            return false;
        }

        // 3. Verificar se o estado atual do jogo permite a ação
        if (game.CurrentState != requiredState)
        {
            _logger.LogWarning($"Invalid game state for action in room {roomId}. Player: {playerId}, Required: {requiredState}, Current: {game.CurrentState}");
            SendErrorAsync(connectionId, $"Action not allowed in current game state ({game.CurrentState}). Required: {requiredState}.").Wait();
            return false;
        }

        // 4. [Opcional mas recomendado] Verificar se é o turno do jogador (para HIT/STAND)
        if (requiredState == GameState.PlayerTurn)
        {
             // Comparar playerId com o jogador no game.CurrentPlayerIndex
             if (game.CurrentPlayerIndex < 0 || game.CurrentPlayerIndex >= game.Players.Count || game.Players[game.CurrentPlayerIndex].PlayerId != playerId)
             {
                 string currentPlayerName = (game.CurrentPlayerIndex >= 0 && game.CurrentPlayerIndex < game.Players.Count) ? game.Players[game.CurrentPlayerIndex].Name : "N/A";
                 _logger.LogWarning($"Not player's turn in room {roomId}. Player: {playerId}, Expected Turn: {currentPlayerName} (Index: {game.CurrentPlayerIndex})");
                 SendErrorAsync(connectionId, "It's not your turn.").Wait();
                 return false;
             }
        }


        // Se todas as validações passaram
        return true;
    }

    // Validação básica para encontrar player, room (usado por StartGame)
    // Assinatura mantida para compatibilidade com chamadas existentes
    private bool ValidatePlayerAndRoom(string connectionId, JsonElement payload,
                                        out string? playerId, out string? roomId, out GameRoom? room, out WebSocket? socket)
    {
        playerId = null;
        roomId = null;
        room = null;
        socket = null;

        if (!_connectionIdToPlayerId.TryGetValue(connectionId, out playerId) || string.IsNullOrEmpty(playerId))
        {
            SendErrorAsync(connectionId, "Player ID not found. Cannot process message.").Wait();
            return false;
        }

        roomId = FindRoomByPlayerId(playerId);
        if (string.IsNullOrEmpty(roomId) || !_rooms.TryGetValue(roomId, out room) || room == null)
        {
            SendErrorAsync(connectionId, "Room not found. Action requires being in a room.").Wait();
            return false;
        }

        if (!_sockets.TryGetValue(connectionId, out socket) || socket == null || socket.State != WebSocketState.Open)
        {
            _logger.LogWarning($"WebSocket connection not found or not open for {connectionId} (Player: {playerId}, Room: {roomId}).");
            // Não enviar erro aqui pode causar loop se a conexão estiver fechando
            return false;
        }
        return true;
    }


    // Envia o estado atual do jogo para todos os jogadores na sala
    private async Task BroadcastGameStateAsync(GameRoom room, object gameState)
    {
        _logger.LogInformation($"Broadcasting GAME_STATE to room {room.Id}");
        var message = new { type = "GAME_STATE", payload = gameState };

        List<Task> sendTasks = new List<Task>();
        List<string> playersInRoom;
        lock(room.Players) { playersInRoom = new List<string>(room.Players); } // Copia segura

        foreach (var playerId in playersInRoom) // Itera sobre a cópia
        {
            // Encontrar o ID da conexão atual do jogador
            if (_playerIdToConnectionId.TryGetValue(playerId, out var targetConnectionId) && targetConnectionId != null)
            {
                 sendTasks.Add(SendMessageAsync(targetConnectionId, message));
            }
            else
            {
                _logger.LogWarning($"Could not find active connection for player {playerId} in room {room.Id} to broadcast game state.");
            }
        }
         // Espera todas as tarefas de envio completarem
        try
        {
             await Task.WhenAll(sendTasks);
             _logger.LogInformation($"Successfully broadcast GAME_STATE to {sendTasks.Count} player(s) in room {room.Id}.");
        }
        catch(Exception ex)
        {
            _logger.LogError($"Exception during Task.WhenAll for BroadcastGameStateAsync in room {room.Id}: {ex.Message}");
            // Pode ser útil logar quais tarefas falharam, se possível
        }
    }

    // Enviar mensagem JSON para um cliente específico
    private async Task SendMessageAsync(string connectionId, object messagePayload)
    {
        if (_sockets.TryGetValue(connectionId, out WebSocket? socket) && socket.State == WebSocketState.Open)
        {
            try
            {
                // Usar CamelCase para compatibilidade com JavaScript/Python
                string messageJson = JsonSerializer.Serialize(messagePayload, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
                byte[] messageBytes = Encoding.UTF8.GetBytes(messageJson);
                // Usar CancellationToken.None para garantir a tentativa de envio mesmo se a conexão estiver fechando
                await socket.SendAsync(new ArraySegment<byte>(messageBytes), WebSocketMessageType.Text, true, CancellationToken.None);
                 _logger.LogDebug($"Sent to {connectionId}: {messageJson.Substring(0, Math.Min(messageJson.Length, 200))}{(messageJson.Length > 200 ? "..." : "")}");
            }
            catch (WebSocketException ex) when (ex.WebSocketErrorCode == WebSocketError.ConnectionClosedPrematurely || ex.WebSocketErrorCode == WebSocketError.InvalidState)
            {
                 _logger.LogError($"WebSocketException (Closed/Invalid State) sending to {connectionId}: {ex.WebSocketErrorCode} - {ex.Message}");
                 // A conexão já está fechada ou em estado inválido, iniciar limpeza
                 await OnDisconnectedAsync(connectionId);
            }
            catch (ObjectDisposedException) // Socket pode ter sido disposed durante a operação
            {
                 _logger.LogError($"ObjectDisposedException sending to {connectionId}. Socket likely closed.");
                 await OnDisconnectedAsync(connectionId);
            }
            catch (JsonException jsonEx)
            {
                 _logger.LogError($"JsonException serializing message for {connectionId}: {jsonEx.Message}");
                 // Não necessariamente desconecta por erro de serialização
            }
            catch (Exception ex) // Outras exceções
            {
                _logger.LogError($"Error sending message to {connectionId}: {ex.GetType().Name} - {ex.Message}");
                 // Erro genérico, pode indicar problema na conexão
                 await OnDisconnectedAsync(connectionId);
            }
        }
         else
         {
             // Socket não encontrado ou não está aberto
             if (!_sockets.ContainsKey(connectionId))
             {
                  _logger.LogWarning($"Attempted to send message to non-existent socket ID: {connectionId}");
             }
             else if (socket != null) // Se socket foi encontrado mas não está aberto
             {
                  _logger.LogWarning($"Attempted to send message to socket {connectionId} but state was {socket.State}");
                  // Se o socket não está aberto, provavelmente já foi ou está sendo desconectado.
                  // Chamar OnDisconnectedAsync aqui pode ser redundante se já foi chamado, mas garante limpeza.
                  await OnDisconnectedAsync(connectionId);
             } else {
                  // Socket foi null, já removido provavelmente
                   _logger.LogWarning($"Attempted to send message to socket ID {connectionId} which was not found in dictionary.");
             }
         }
    }

    // Enviar mensagem de erro para um cliente específico
    private Task SendErrorAsync(string connectionId, string errorMessage)
    {
        _logger.LogWarning($"Sending ERROR to {connectionId}: {errorMessage}");
        return SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = errorMessage } });
    }

    // Método chamado quando um cliente se desconecta ou ocorre um erro grave
    private async Task OnDisconnectedAsync(string connectionId)
    {
        // Tenta remover o socket do dicionário principal
        if (_sockets.TryRemove(connectionId, out WebSocket? socket))
        {
            _logger.LogInformation($"WebSocket disconnected: {connectionId}. Cleaning up resources.");

            // Fecha o socket se ainda não estiver fechado (garante)
            if (socket != null && (socket.State == WebSocketState.Open || socket.State == WebSocketState.CloseReceived || socket.State == WebSocketState.CloseSent))
            {
                 try
                 {
                     // Usar um timeout curto para não bloquear indefinidamente
                     using var cts = new CancellationTokenSource(TimeSpan.FromSeconds(2));
                     await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Server cleaning up", cts.Token);
                 }
                 catch (OperationCanceledException)
                 {
                      _logger.LogWarning($"Timeout closing socket {connectionId} during cleanup.");
                 }
                 catch(ObjectDisposedException){ /* Already disposed */ }
                 catch (Exception ex)
                 {
                      _logger.LogError($"Exception closing socket {connectionId} during cleanup: {ex.Message}");
                 }
            }
            socket?.Dispose(); // Libera recursos do socket

             // Encontra o ID do jogador associado a esta conexão
            if (_connectionIdToPlayerId.TryRemove(connectionId, out string? playerId) && playerId != null)
            {
                 string playerName = GetPlayerName(playerId); // Pega nome antes de remover o mapeamento
                 _logger.LogInformation($"Player {playerName} ({playerId}) associated with connection {connectionId} is now disconnected.");
                 _playerIdToName.TryRemove(playerId, out _); // Remove mapeamento de nome
                 _playerIdToConnectionId.TryRemove(playerId, out _); // Remove mapeamento reverso

                 // Notificar saída da sala se estava em uma (usará playerId para encontrar a sala)
                 // Passamos um JsonElement default pois não temos payload na desconexão
                 // HandleLeaveRoomAsync agora também remove _playerIdToRoomId
                 await HandleLeaveRoomAsync(connectionId); // Pass connectionId, HandleLeave uses it to find playerId if needed
            }
             else
             {
                  _logger.LogWarning($"Could not find Player ID for disconnected connection {connectionId}. No room cleanup performed for this ID.");
             }

        }
         // else: Se TryRemove falhar, já foi removido por outra chamada, não precisa logar como erro
    }


     // Método auxiliar de limpeza de salas (exemplo, pode precisar de ajustes)
    private async Task CleanupInactiveRoomsAsync(CancellationToken cancellationToken)
     {
         while (!cancellationToken.IsCancellationRequested)
         {
             await Task.Delay(TimeSpan.FromMinutes(10), cancellationToken); // Verifica a cada 10 minutos

             var roomsToRemove = new List<string>();
             foreach (var roomPair in _rooms)
             {
                 var room = roomPair.Value;
                 // Critério de inatividade: sala vazia E não em progresso
                 // Poderia adicionar um timestamp da última atividade se necessário
                 bool isEmpty;
                 lock (room.Players) { isEmpty = room.Players.Count == 0; }

                 if (isEmpty && !room.IsInProgress)
                 {
                      _logger.LogInformation($"Room '{room.Name}' ({room.Id}) is empty and inactive. Scheduling for removal.");
                     roomsToRemove.Add(roomPair.Key);
                 }
             }

             foreach (var roomId in roomsToRemove)
             {
                 if (_rooms.TryRemove(roomId, out GameRoom? removedRoom))
                 {
                     _logger.LogInformation($"Removed inactive room '{removedRoom.Name}' ({roomId}).");
                     // Limpar instância de jogo associada
                      if (_games.TryRemove(roomId, out BlackjackGame? gameInstance))
                      {
                           _logger.LogInformation($"Removed BlackjackGame instance for cleaned up room {roomId}.");
                           // gameInstance.Dispose(); // Se necessário
                      }

                     // Limpar mapeamentos de jogadores que pudessem estar presos a esta sala (segurança)
                     var playersToRemoveMapping = _playerIdToRoomId.Where(kvp => kvp.Value == roomId).Select(kvp => kvp.Key).ToList();
                     foreach(var pId in playersToRemoveMapping)
                     {
                         _playerIdToRoomId.TryRemove(pId, out _);
                         _logger.LogWarning($"Removed lingering player->room mapping for player {pId} in cleaned up room {roomId}.");
                     }
                 }
             }
         }
     }


    // Envia mensagem para todos em uma sala específica
     private async Task BroadcastMessageToRoomAsync(string roomId, object messagePayload, string? excludePlayerId = null)
     {
         if (!_rooms.TryGetValue(roomId, out GameRoom? room) || room == null)
         {
             _logger.LogWarning($"Attempted to broadcast to non-existent room: {roomId}");
             return;
         }

         List<Task> sendTasks = new List<Task>();
         List<string> playersInRoom;
         lock (room.Players) // Lê a lista de jogadores de forma segura
         {
             playersInRoom = new List<string>(room.Players);
         }

         foreach (string playerIdInRoom in playersInRoom)
         {
             if (playerIdInRoom == excludePlayerId &&
                 _playerIdToConnectionId.TryGetValue(playerIdInRoom, out string? connId) &&
                 connId != null)
             {
                 // Encontrou o connectionId do jogador na sala
                 sendTasks.Add(SendMessageAsync(connId, messagePayload));
             }
             else if (playerIdInRoom != excludePlayerId)
             {
                 _logger.LogWarning($"Could not find connection ID for player {playerIdInRoom} in room {roomId} during broadcast.");
             }
         }

         if (sendTasks.Count > 0)
         {
              _logger.LogInformation($"Broadcasting message to {sendTasks.Count} players in room {roomId} ('{room.Name}').");
             await Task.WhenAll(sendTasks);
         }
     }

    private string GetPlayerName(string playerId)
    {
        return _playerIdToName.TryGetValue(playerId, out var name) ? name ?? "Unknown" : "Unknown";
    }

     private string? FindRoomByPlayerId(string playerId)
     {
         if (_playerIdToRoomId.TryGetValue(playerId, out string? roomId))
         {
             if (_rooms.ContainsKey(roomId))
             {
                return roomId;
             }
             else
             {
                 _logger.LogWarning($"Player {playerId} was mapped to room {roomId}, but room does not exist. Cleaning up mapping.");
                 _playerIdToRoomId.TryRemove(playerId, out _);
                 return null;
             }
         }
         return null; // Jogador não encontrado em nenhuma sala
     }

} // Fim da classe WebSocketManager