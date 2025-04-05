using Server.Models; // Ainda pode precisar de GameRoom e outros
using System.Net.WebSockets;
using System.Text;
using System.Text.Json; // Para serializar/desserializar JSON
using Microsoft.Extensions.Logging;
using System.Collections.Concurrent; // Para ConcurrentDictionary
using System.Threading;
using System.Threading.Tasks;

namespace Server.Services;

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

    // Manter a lógica das salas (talvez precise adaptar GameRoom)
    private readonly ConcurrentDictionary<string, GameRoom> _rooms = new ConcurrentDictionary<string, GameRoom>();
    private readonly ILogger<WebSocketManager> _logger;

    // Usando ILogger<WebSocketManager> agora
    public WebSocketManager(ILogger<WebSocketManager> logger)
    {
        _logger = logger;
        LogInformation("WebSocket Manager Initialized.");
        // Iniciar tarefa de limpeza de salas inativas (opcional, pode ser reativada)
        // _ = Task.Run(async () => await CleanupInactiveRoomsAsync(CancellationToken.None));
    }

    // Método chamado pelo Startup para lidar com uma nova conexão WebSocket
    public async Task HandleWebSocketAsync(WebSocket webSocket, CancellationToken cancellationToken)
    {
        string connectionId = Guid.NewGuid().ToString(); // Gera um ID único para a conexão
        _sockets.TryAdd(connectionId, webSocket);
        LogInformation($"WebSocket connected: {connectionId}");

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
            LogInformation($"WebSocket {connectionId} closed prematurely: {ex.Message}");
        }
        catch (OperationCanceledException)
        {
            LogInformation($"WebSocket {connectionId} operation canceled (client disconnected).");
        }
        catch (Exception ex)
        {
            LogError($"Error handling WebSocket {connectionId}: {ex.GetType().Name} - {ex.Message}");
            // Tentar fechar o socket graciosamente em caso de erro não esperado
            if (webSocket.State == WebSocketState.Open || webSocket.State == WebSocketState.CloseReceived || webSocket.State == WebSocketState.CloseSent)
            {
                await webSocket.CloseAsync(WebSocketCloseStatus.InternalServerError, "Server error", cancellationToken);
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
                    LogInformation("ReceiveMessageAsync: Connection closed prematurely.");
                    return null;
                }
                catch (OperationCanceledException)
                {
                     LogInformation("ReceiveMessageAsync: Operation canceled.");
                    return null; // Sai se a operação for cancelada
                }

                if (result.MessageType == WebSocketMessageType.Close)
                {
                    LogInformation("ReceiveMessageAsync: Received close message.");
                    // Tenta completar o handshake de fechamento
                     if (webSocket.State == WebSocketState.CloseReceived)
                     {
                          await webSocket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "Client requested closure", CancellationToken.None);
                     }
                    return null; // Indica que a conexão deve ser fechada
                }
                 if (result.MessageType != WebSocketMessageType.Text)
                 {
                     LogWarning($"ReceiveMessageAsync: Received non-text message type: {result.MessageType}");
                     continue; // Ignora mensagens não-texto por enquanto
                 }

                ms.Write(buffer.Array!, buffer.Offset, result.Count);

            } while (!result.EndOfMessage && !cancellationToken.IsCancellationRequested);

             if (cancellationToken.IsCancellationRequested)
             {
                  LogInformation("ReceiveMessageAsync: Cancellation requested during message reception.");
                 return null;
             }

            ms.Seek(0, SeekOrigin.Begin);
            using (var reader = new StreamReader(ms, Encoding.UTF8))
            {
                return await reader.ReadToEndAsync(cancellationToken);
            }
        }
    }

    // Processa uma mensagem JSON recebida de um cliente
    private async Task ProcessMessageAsync(string connectionId, string messageJson)
    {
        LogInformation($"[WebSocket {connectionId}] Received JSON: {messageJson}");
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
                             await HandleLeaveRoomAsync(connectionId, payloadElement);
                            break;
                        // Adicionar outros casos: GAME_ACTION, CHAT, etc.
                        default:
                            LogWarning($"Unknown message type received from {connectionId}: {messageType}");
                             await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = $"Unknown message type: {messageType}" } });
                            break;
                    }
                }
                 else
                 {
                     LogWarning($"Invalid message format from {connectionId}: missing 'type' property.");
                     await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Invalid message format: 'type' is required." } });
                 }
            }
        }
        catch (JsonException jsonEx)
        {            
            LogError($"Invalid JSON received from {connectionId}: {jsonEx.Message}");
             await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Invalid JSON format." } });
        }
        catch (Exception ex)
        {
            LogError($"Error processing message from {connectionId}: {ex.Message}");
             await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Internal server error processing message." } });
        }
    }

    // --- Handlers específicos para tipos de mensagem --- //

     private Task HandleSetNameAsync(string connectionId, JsonElement payload)
    {
        string? name = payload.TryGetProperty("name", out var n) ? n.GetString() : null;
        if (string.IsNullOrWhiteSpace(name))
        {
            return SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Name cannot be empty." } });
        }

        // Remover mapeamentos antigos se o jogador já existia com outro nome/conexão (opcional)
        if (_connectionIdToPlayerId.TryGetValue(connectionId, out var existingPlayerId) && existingPlayerId != null)
        {
             _playerIdToName.TryRemove(existingPlayerId, out _);
             _playerIdToConnectionId.TryRemove(existingPlayerId, out _);
             // Não remover de _playerIdToRoomId aqui, pois ele pode estar numa sala
        }

        string playerId = Guid.NewGuid().ToString(); // Gera um ID de jogador
        _connectionIdToPlayerId[connectionId] = playerId;
        _playerIdToName[playerId] = name;
        _playerIdToConnectionId[playerId] = connectionId; // Mapeia playerId para connectionId
        LogInformation($"Connection {connectionId} set name to '{name}' (PlayerID: {playerId})");
        // Enviar confirmação (opcional)
        return SendMessageAsync(connectionId, new { type = "NAME_SET", payload = new { playerId = playerId, name = name } });
    }

    private async Task HandleListRoomsAsync(string connectionId)
    {
        LogInformation($"Handling LIST_ROOMS request from {connectionId}");
        // Adapta o formato de GetAvailableRooms para o cliente
        var availableRooms = _rooms.Values
            .Where(r => !r.IsInProgress && r.Players.Count < r.MaxPlayers)
            .Select(r => new {
                id = r.Id,
                name = r.Name,
                playerCount = r.Players.Count, // Precisa adaptar r.Players para conter IDs/Nomes
                hasPassword = !string.IsNullOrEmpty(r.Password),
                hostName = GetPlayerName(r.HostPlayerId) // Assumindo que GameRoom tem HostPlayerId
            })
            .ToList();

         await SendMessageAsync(connectionId, new { type = "ROOMS_LIST", payload = availableRooms });
    }

     private async Task HandleCreateRoomAsync(string connectionId, JsonElement payload)
    {
        if (!_connectionIdToPlayerId.TryGetValue(connectionId, out string? hostPlayerId) || hostPlayerId == null)
        {
            await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Player name not set. Send SET_NAME first." } });
            return;
        }

        string? roomName = payload.TryGetProperty("roomName", out var rn) ? rn.GetString() : "Sala Padrão";
        string? password = payload.TryGetProperty("password", out var pw) ? pw.GetString() : null;
        int maxPlayers = payload.TryGetProperty("maxPlayers", out var mp) && mp.TryGetInt32(out int mpVal) ? mpVal : 8;

        // Validação básica
        if (string.IsNullOrWhiteSpace(roomName)) roomName = $"Sala de {GetPlayerName(hostPlayerId)}";

        var newRoom = new GameRoom(roomName, maxPlayers, password)
        {
            HostPlayerId = hostPlayerId // Assumindo que GameRoom tem HostPlayerId
            // Adicionar host à lista de jogadores da sala
            // TODO: Adaptar GameRoom.Players para usar Player IDs
        };
         newRoom.AddPlayer(hostPlayerId); // Adaptar AddPlayer para aceitar ID

        if (_rooms.TryAdd(newRoom.Id, newRoom))
        {
            LogInformation($"Room '{roomName}' (ID: {newRoom.Id}) created by Player {hostPlayerId} ({GetPlayerName(hostPlayerId)}) - Conn: {connectionId}");
            // Adicionar o criador à sala (precisa adaptar GameRoom)
             // room.Players.Add(???); 

             // Envia confirmação para o criador
             await SendMessageAsync(connectionId, new { type = "ROOM_CREATED", payload = new { roomId = newRoom.Id, name = newRoom.Name, hostPlayerId = hostPlayerId } });
            
             // Notificar outros jogadores sobre a nova sala (opcional)
             // await BroadcastMessageAsync(new { type = "NEW_ROOM", payload = new { id=newRoom.Id, name=newRoom.Name, hostName=GetPlayerName(hostPlayerId) } }, excludeConnectionId: connectionId);
        }
        else
        {            
            LogError($"Failed to add room '{roomName}' to dictionary.");
             await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Failed to create room on server." } });
        }
    }

    private async Task HandleJoinRoomAsync(string connectionId, JsonElement payload)
    {
         if (!_connectionIdToPlayerId.TryGetValue(connectionId, out string? joiningPlayerId) || joiningPlayerId == null)
        {
            await SendMessageAsync(connectionId, new { type = "ERROR", payload = new { message = "Player name not set. Send SET_NAME first." } });
            return;
        }
        
        string? roomId = payload.TryGetProperty("roomId", out var rid) ? rid.GetString() : null;
        string? password = payload.TryGetProperty("password", out var pw) ? pw.GetString() : "";

        if (roomId == null || !_rooms.TryGetValue(roomId, out GameRoom? room) || room == null)
        {
             await SendMessageAsync(connectionId, new { type = "JOIN_ERROR", payload = new { message = "Room not found." } });
            return;
        }

        // Verificar senha
         if (!string.IsNullOrEmpty(room.Password) && room.Password != password)
         {
             await SendMessageAsync(connectionId, new { type = "JOIN_ERROR", payload = new { message = "Invalid password." } });
             return;
         }

         // Verificar capacidade e estado
        if (!room.CanJoin()) // Assumindo que CanJoin verifica MaxPlayers e IsInProgress
        {
             await SendMessageAsync(connectionId, new { type = "JOIN_ERROR", payload = new { message = "Room is full or game is in progress." } });
            return;
        }

        // Adicionar jogador à sala (precisa adaptar GameRoom)
        if (room.AddPlayer(joiningPlayerId)) // Adaptar AddPlayer para aceitar ID e retornar bool
        {
            LogInformation($"Player {joiningPlayerId} ({GetPlayerName(joiningPlayerId)}) joined room {roomId} - Conn: {connectionId}");

            // Mapear connectionId para roomId (para saber onde o jogador está)
            // TODO: Adicionar _connectionIdToRoomId dictionary -> USANDO _playerIdToRoomId
            _playerIdToRoomId[joiningPlayerId] = roomId; // Adiciona mapeamento player -> room

             // Enviar sucesso para quem entrou
             // Enviar P2P host address? O WebSocket PODE ser o P2P?\
             // Por simplicidade inicial, vamos assumir que a comunicação do jogo também passará pelo WebSocket do servidor.
             // Se quisermos P2P real, o host precisa informar seu IP:PORT de escuta P2P.
             var playersInRoom = room.Players.Select(pId => new { id = pId, name = GetPlayerName(pId) }).ToList();
            await SendMessageAsync(connectionId, new { 
                type = "JOIN_SUCCESS", 
                payload = new { 
                    roomId = room.Id, 
                    name = room.Name, 
                    hostPlayerId = room.HostPlayerId, 
                    players = playersInRoom 
                    // p2pHostAddress = GetP2PAddressForHost(room.HostPlayerId) // Se P2P for separado
                } 
            });

            // Notificar outros jogadores na sala
             var joinNotification = new { type = "PLAYER_JOINED", payload = new { roomId = room.Id, player = new { id = joiningPlayerId, name = GetPlayerName(joiningPlayerId) } } };
             await BroadcastMessageToRoomAsync(roomId, joinNotification, excludePlayerId: joiningPlayerId);
        }
        else
        {            
             await SendMessageAsync(connectionId, new { type = "JOIN_ERROR", payload = new { message = "Failed to add player to the room." } });
        }
    }

     private async Task HandleLeaveRoomAsync(string connectionId, JsonElement payload) // payload pode ser default se chamado por OnDisconnectedAsync
     {
         // Usa o mapeamento reverso se disponível, senão o ID da conexão
         string? leavingPlayerId = null;
         if (!_connectionIdToPlayerId.TryGetValue(connectionId, out leavingPlayerId) || leavingPlayerId == null)
         {
             // Tenta encontrar pelo payload (se foi uma chamada direta e não desconexão)
             if (payload.ValueKind == JsonValueKind.Object && payload.TryGetProperty("playerId", out var pIdElement))
             {
                 leavingPlayerId = pIdElement.GetString();
             }
             
             if (leavingPlayerId == null)
             {
                 LogWarning($"Cannot handle LEAVE_ROOM/disconnect for unknown connection: {connectionId}");
                 return; // Jogador não identificado ou já saiu
             }
         }

         // Encontra a sala usando o novo mapeamento eficiente
         string? roomId = FindRoomByPlayerId(leavingPlayerId);
         if (roomId == null || !_rooms.TryGetValue(roomId, out GameRoom? room) || room == null)
         {
             LogWarning($"Player {leavingPlayerId} tried to leave but was not found in any room.");
             // Garante que o mapeamento player->room seja removido caso exista por inconsistência
             _playerIdToRoomId.TryRemove(leavingPlayerId, out _);
             return; // Jogador não estava em uma sala conhecida
         }

         LogInformation($"Handling LEAVE_ROOM for Player {leavingPlayerId} from Room {roomId} - Conn: {connectionId}");

         bool removed = room.RemovePlayer(leavingPlayerId); // Remove jogador da sala

         // Remover mapeamento player -> room ANTES de verificar se a sala está vazia
         _playerIdToRoomId.TryRemove(leavingPlayerId, out _);

         if (removed)
         {
             // Notificar outros jogadores na sala
             var leaveNotification = new { type = "PLAYER_LEFT", payload = new { roomId = room.Id, playerId = leavingPlayerId } };
             await BroadcastMessageToRoomAsync(roomId, leaveNotification, excludePlayerId: leavingPlayerId); // Excluir quem saiu

             // Verificar se a sala ficou vazia ou se precisa de novo host
             if (room.Players.Count == 0)
             {
                 LogInformation($"Room {roomId} ('{room.Name}') is empty after player {leavingPlayerId} left. Removing room.");
                 _rooms.TryRemove(roomId, out _);
                 // Opcional: Notificar alguém que a sala foi removida? (Provavelmente não necessário)
             }
             else if (room.HostPlayerId == leavingPlayerId) // Se o host saiu
             {
                 LogInformation($"Host {leavingPlayerId} left room {roomId}. Assigning new host...");
                 room.AssignNewHost(); // Lógica do GameRoom para designar novo host
                 var newHostId = room.HostPlayerId;
                 if (!string.IsNullOrEmpty(newHostId))
                 {
                      LogInformation($"New host for room {roomId} is {newHostId} ({GetPlayerName(newHostId)})");
                      var hostNotification = new { type = "NEW_HOST", payload = new { roomId = room.Id, hostId = newHostId, hostName = GetPlayerName(newHostId) } };
                      await BroadcastMessageToRoomAsync(roomId, hostNotification);
                 }
                 else
                 {
                     // Isso não deveria acontecer se AssignNewHost foi chamado e room.Players.Count > 0
                      LogWarning($"Room {roomId} has players but failed to assign a new host.");
                 }
             }
         }
         else
         {
             // Isso pode acontecer se o jogador já foi removido por outra thread (ex: desconexão simultânea)
             LogWarning($"Player {leavingPlayerId} was already removed from room {roomId} or was not found in its player list.");
         }
          // Enviar confirmação para quem saiu (opcional, pode ser confuso se foi desconexão)
          // await SendMessageAsync(connectionId, new { type = "LEFT_ROOM", payload = new { roomId = roomId } });
     }

    // --- Fim Handlers --- //

    // Limpeza quando um WebSocket é desconectado
    private async Task OnDisconnectedAsync(string connectionId)
    {
        if (_sockets.TryRemove(connectionId, out WebSocket? socket))
        {            
            LogInformation($"WebSocket disconnected: {connectionId}");
            // Tentar fechar graciosamente se ainda não estiver fechado
            if (socket.State == WebSocketState.Open || socket.State == WebSocketState.CloseReceived || socket.State == WebSocketState.CloseSent)
            {
                 try { await socket.CloseAsync(WebSocketCloseStatus.NormalClosure, "Client disconnected", CancellationToken.None); } catch { /* Ignorar erros no fechamento */ }
            }
            socket.Dispose();
        }
        
        // Remover jogador associado à conexão
        if (_connectionIdToPlayerId.TryRemove(connectionId, out string? playerId) && playerId != null)
        {
             // Remover dos outros mapeamentos
             _playerIdToName.TryRemove(playerId, out _);
             _playerIdToConnectionId.TryRemove(playerId, out _); // Remove mapeamento player -> connection
             LogInformation($"Player {playerId} mappings removed due to connection {connectionId} closure.");

             // Notificar saída da sala se estava em uma (usará playerId para encontrar a sala)
             // Passamos um JsonElement default pois não temos payload na desconexão
             await HandleLeaveRoomAsync(connectionId, default(JsonElement));
        }
        else
        {
             LogWarning($"No player found associated with disconnected connection {connectionId}.");
        }
    }

    // Envia uma mensagem JSON para um cliente específico
    private async Task SendMessageAsync(string connectionId, object messagePayload)
    {
        if (_sockets.TryGetValue(connectionId, out WebSocket? socket) && socket.State == WebSocketState.Open)
        {
            try
            {
                string messageJson = JsonSerializer.Serialize(messagePayload, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
                var buffer = Encoding.UTF8.GetBytes(messageJson);
                await socket.SendAsync(new ArraySegment<byte>(buffer), WebSocketMessageType.Text, true, CancellationToken.None);
                 LogInformation($"[WebSocket {connectionId}] Sent: {messageJson}");
            }
            catch (WebSocketException ex) when (ex.WebSocketErrorCode == WebSocketError.ConnectionClosedPrematurely || ex.WebSocketErrorCode == WebSocketError.InvalidState)
            {
                 LogWarning($"Failed to send message to {connectionId} (connection closing): {ex.Message}");
                 // Agendar remoção da conexão se falhar ao enviar
                 await OnDisconnectedAsync(connectionId);
            }
            catch (Exception ex)
            {
                LogError($"Error sending message to {connectionId}: {ex.Message}");
                 await OnDisconnectedAsync(connectionId); // Remover em caso de outros erros
            }
        }
        else
        {            
             LogWarning($"Attempted to send message to disconnected or non-existent socket: {connectionId}");
        }
    }

    // Envia uma mensagem JSON para todos os clientes conectados
    private async Task BroadcastMessageAsync(object messagePayload, string? excludeConnectionId = null)
    {
        List<Task> sendTasks = new List<Task>();
        foreach (var pair in _sockets)
        {
            if (pair.Key != excludeConnectionId && pair.Value.State == WebSocketState.Open)
            {
                sendTasks.Add(SendMessageAsync(pair.Key, messagePayload));
            }
        }
        await Task.WhenAll(sendTasks);
    }

     // Envia mensagem para todos em uma sala específica
     private async Task BroadcastMessageToRoomAsync(string roomId, object messagePayload, string? excludePlayerId = null)
     {
         if (!_rooms.TryGetValue(roomId, out GameRoom? room) || room == null)
         {
             LogWarning($"Attempted to broadcast to non-existent room: {roomId}");
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
             if (playerIdInRoom != excludePlayerId &&
                 _playerIdToConnectionId.TryGetValue(playerIdInRoom, out string? connId) &&
                 connId != null)
             {
                 // Encontrou o connectionId do jogador na sala
                 sendTasks.Add(SendMessageAsync(connId, messagePayload));
             }
             else if (playerIdInRoom != excludePlayerId)
             {
                 LogWarning($"Could not find connection ID for player {playerIdInRoom} in room {roomId} during broadcast.");
             }
         }

         if (sendTasks.Count > 0)
         {
              LogInformation($"Broadcasting message to {sendTasks.Count} players in room {roomId} ('{room.Name}').");
             await Task.WhenAll(sendTasks);
         }
     }

    // --- Métodos auxiliares (precisam ser implementados/adaptados) --- //
    private string GetPlayerName(string playerId)
    {
        return _playerIdToName.TryGetValue(playerId, out var name) ? name ?? "Unknown" : "Unknown";
    }

     private string? FindRoomByPlayerId(string playerId)
     {
         // TODO: Implementar busca eficiente (talvez usando _connectionIdToRoomId e _connectionIdToPlayerId)
         // IMPLEMENTADO: Usando o novo dicionário _playerIdToRoomId
         if (_playerIdToRoomId.TryGetValue(playerId, out string? roomId))
         {
             // Verifica se a sala ainda existe (segurança extra)
             if (_rooms.ContainsKey(roomId))
             {
                return roomId;
             }
             else
             {
                 // Inconsistência: jogador mapeado para sala inexistente. Limpar.
                 LogWarning($"Player {playerId} was mapped to room {roomId}, but room does not exist. Cleaning up mapping.");
                 _playerIdToRoomId.TryRemove(playerId, out _);
                 return null;
             }
         }
         return null; // Jogador não encontrado em nenhuma sala
         /* // Código antigo ineficiente:
         foreach (var roomPair in _rooms)
         {
             if (roomPair.Value.Players.Contains(playerId)) // Assumindo que Players é List<string> com IDs
             {
                 return roomPair.Key;
             }
         }
         return null;
         */
     }

    // TODO: Implementar GetP2PAddressForHost se for usar P2P separado
    // TODO: Adaptar a classe GameRoom para usar Player IDs em vez de ClientHandler/objetos

    // --- Logging --- //
    private void LogInformation(string message)
    {
        _logger?.LogInformation(message);
        Console.WriteLine($"[INFO] {message}"); // Log no console também
    }

    private void LogWarning(string message)
    {
        _logger?.LogWarning(message);
        Console.WriteLine($"[WARN] {message}");
    }

    private void LogError(string message)
    {
        _logger?.LogError(message);
        Console.WriteLine($"[ERROR] {message}");
    }
} 