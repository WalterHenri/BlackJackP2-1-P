using System.Text.Json;
using System.Collections.Concurrent; // Para thread-safe

namespace Server.Models;

public class GameRoom
{
    public string Id { get; set; } // ID único da sala
    public string Name { get; set; } // Nome da sala
    public string? Password { get; set; } // Senha (pode ser nula)
    public int MaxPlayers { get; set; }
    public List<string> Players { get; private set; } // Lista de Player IDs (strings)
    public string HostPlayerId { get; set; } = string.Empty; // ID do jogador que criou a sala
    public bool IsInProgress { get; set; }
    // GameState pode precisar de adaptação dependendo da lógica do jogo
    public ConcurrentDictionary<string, object> GameState { get; set; }

    // Construtor adaptado
    public GameRoom(string name, int maxPlayers, string? password = null)
    {
        Id = Guid.NewGuid().ToString("N").Substring(0, 8);
        Name = name;
        Password = password; // Pode ser nulo
        MaxPlayers = maxPlayers;
        Players = new List<string>();
        IsInProgress = false;
        GameState = new ConcurrentDictionary<string, object>();
        // HostPlayerId deve ser setado após a criação pelo WebSocketManager
    }

    // Método para adicionar um jogador (por ID)
    public bool AddPlayer(string playerId)
    {
        lock (Players) // Bloqueio para modificar a lista
        {
            if (Players.Count < MaxPlayers && !Players.Contains(playerId))
            {
                Players.Add(playerId);
                return true;
            }
        }
        return false;
    }

    // Método para remover um jogador (por ID)
    public bool RemovePlayer(string playerId)
    {
        lock (Players)
        {
            return Players.Remove(playerId);
        }
    }

    // Verifica se é possível entrar na sala
    public bool CanJoin()
    {
        // A verificação de senha é feita antes no WebSocketManager
        lock (Players)
        {
            return Players.Count < MaxPlayers && !IsInProgress;
        }
    }

    // Método BroadcastMessage removido - será feito pelo WebSocketManager
    // public void BroadcastMessage(string message, string excludePlayerId = null) { ... }

    // Método UpdateGameState removido - Lógica de estado do jogo pode ser gerenciada
    // diretamente pelo WebSocketManager ou por uma classe de jogo dedicada.
    // public void UpdateGameState(Dictionary<string, object> newState) { ... }

    // Lógica para definir novo host (exemplo)
    public void AssignNewHost()
    {
        lock (Players)
        {
            if (Players.Count > 0)
            {
                HostPlayerId = Players[0]; // O jogador mais antigo se torna o host
            }
            else
            {
                HostPlayerId = string.Empty; // Ninguém para ser host
            }
        }
    }
}