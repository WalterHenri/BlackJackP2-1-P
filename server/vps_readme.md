# Tutorial de Configuração do Servidor BlackJack P2P em VPS

Este guia apresenta os passos necessários para configurar e executar o servidor BlackJack P2P em um VPS (Servidor Privado Virtual).

## Pré-requisitos

- Um VPS com sistema operacional Linux (Ubuntu/Debian recomendado)
- Python 3.7+ instalado
- Acesso SSH ao servidor
- Domínio (opcional, mas recomendado)

## 1. Configuração Inicial do VPS

### Atualizando o sistema
```bash
sudo apt update
sudo apt upgrade -y
```

### Instalando dependências
```bash
sudo apt install -y python3 python3-pip git ufw
pip3 install --upgrade pip
```

## 2. Configurando o Firewall

Abra as portas necessárias para o funcionamento do servidor:

```bash
sudo ufw allow ssh
sudo ufw allow 5000/tcp  # Porta do servidor de lobby
sudo ufw allow 5001/udp  # Porta para descoberta de jogo
sudo ufw allow 5555/tcp  # Porta padrão para jogos P2P
sudo ufw enable
```

## 3. Clonando o Repositório do Jogo

```bash
git clone https://seu-repositorio/BlackJackP2P.git
cd BlackJackP2P
```

## 4. Instalando Dependências Python

```bash
pip3 install -r requirements.txt
```

Se não existir um arquivo `requirements.txt`, crie um com o seguinte conteúdo:

```
pygame
pynat
requests
```

## 5. Configurando o Servidor

### Ajustando as configurações

Abra o arquivo `client/constants.py` e substitua o valor da variável `VPS_SERVER_HOST` pelo endereço IP público do seu VPS ou nome de domínio:

```python
# Exemplo:
VPS_SERVER_HOST = "seu-vps.exemplo.com"  # ou o IP público
```

## 6. Executando o Servidor como Serviço

Crie um arquivo de serviço systemd para manter o servidor rodando em segundo plano:

```bash
sudo nano /etc/systemd/system/blackjack-server.service
```

Insira o seguinte conteúdo, ajustando os caminhos conforme necessário:

```
[Unit]
Description=BlackJack P2P Server
After=network.target

[Service]
User=seu_usuario
WorkingDirectory=/caminho/para/BlackJackP2P
ExecStart=/usr/bin/python3 /caminho/para/BlackJackP2P/server/deploy_vps.py --host 0.0.0.0
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Ative e inicie o serviço:

```bash
sudo systemctl daemon-reload
sudo systemctl enable blackjack-server
sudo systemctl start blackjack-server
```

Verifique o status:

```bash
sudo systemctl status blackjack-server
```

## 7. Monitorando os Logs do Servidor

Para verificar os logs:

```bash
sudo journalctl -u blackjack-server -f
```

Ou diretamente do arquivo de log:

```bash
tail -f /caminho/para/BlackJackP2P/server/server.log
```

## 8. Configuração de Domínio (Opcional)

Se você possui um domínio, configure um registro DNS "A" para apontar para o IP do seu VPS.

## 9. Testando o Servidor

Você pode testar se o servidor está funcionando corretamente usando:

```bash
curl http://seu-vps:5000/status
```

Este comando deve retornar informações básicas do servidor se estiver funcionando.

## 10. Solução de Problemas Comuns

### Serviço não inicia
Verifique os logs:
```bash
sudo journalctl -u blackjack-server -e
```

### Problemas de conexão
- Verifique se as portas estão abertas: `sudo ufw status`
- Teste se o servidor está ouvindo na porta: `netstat -tulpn | grep 5000`
- Verifique se não há NAT ou firewall do provedor bloqueando

### Jogadores não conseguem se conectar
- Verifique se o IP ou domínio está configurado corretamente
- Teste a conexão com `telnet seu-vps 5000` a partir de uma máquina cliente

## 11. Comandos Úteis para Manutenção

```bash
# Reiniciar o servidor
sudo systemctl restart blackjack-server

# Parar o servidor
sudo systemctl stop blackjack-server

# Ver o uso de recursos
htop

# Verificar espaço em disco
df -h
```

## 12. Backups

Configure backups periódicos dos arquivos de dados do jogador:

```bash
# Criar backup manualmente
tar -czf backup-$(date +%Y%m%d).tar.gz /caminho/para/BlackJackP2P/player_data.txt
```

## 13. Atualizando o Código

Para atualizar o código no servidor:

```bash
cd /caminho/para/BlackJackP2P
git pull
sudo systemctl restart blackjack-server
``` 