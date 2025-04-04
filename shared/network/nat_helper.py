import socket
import threading
import json
import time
import random
import requests
import logging

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('NAT_Helper')

class NATHelper:
    """Classe auxiliar para atravessar NAT e estabelecer conexões P2P."""
    
    def __init__(self, stun_server='stun.l.google.com:19302', relay_server=None):
        """
        Inicializa o auxiliar NAT.
        
        Args:
            stun_server: Servidor STUN para descoberta de endereço público
            relay_server: Servidor de relay para quando conexão direta falhar
        """
        self.stun_server = stun_server
        self.relay_server = relay_server
        self.public_ip = None
        self.public_port = None
        self.nat_type = None
        
    def discover_public_address(self):
        """
        Descobre o endereço IP público e tipo de NAT usando STUN.
        
        Returns:
            tuple: (sucesso, endereço público, tipo de NAT)
        """
        try:
            # Implementação simplificada de STUN
            # Em produção, use uma biblioteca STUN completa
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(3)
            
            # Extrair host e porta do servidor STUN
            stun_host, stun_port_str = self.stun_server.split(':')
            stun_port = int(stun_port_str)
            
            # Enviar solicitação para o servidor STUN
            s.sendto(b'\x00\x01\x00\x00\x21\x12\xA4\x42', (stun_host, stun_port))
            
            # Receber resposta
            data, addr = s.recvfrom(1024)
            
            # Em uma implementação real, parsearíamos a resposta STUN adequadamente
            # Para simplificar, usamos o endereço do qual recebemos a resposta
            self.public_ip = addr[0]
            # Na implementação real, o STUN retornaria a porta mapeada
            self.public_port = random.randint(10000, 60000)  # Simulação
            
            # Determinar tipo de NAT (simplificado)
            self.nat_type = "Unknown"  # Precisaria de mais testes para determinar
            
            logger.info(f"Endereço público descoberto: {self.public_ip}:{self.public_port}")
            return True, f"{self.public_ip}:{self.public_port}", self.nat_type
            
        except Exception as e:
            logger.error(f"Erro ao descobrir endereço público: {e}")
            return False, None, "Error"
        finally:
            s.close()
    
    def punch_hole(self, target_address):
        """
        Realiza um 'hole punching' para estabelecer conexão direta com o alvo.
        
        Args:
            target_address: Endereço do alvo (IP:porta)
            
        Returns:
            bool: Sucesso da operação
        """
        try:
            # Criar socket UDP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(5)
            
            # Extrair IP e porta do alvo
            target_ip, target_port_str = target_address.split(':')
            target_port = int(target_port_str)
            
            # Enviar pacotes para "furar" o NAT
            for _ in range(5):
                s.sendto(b'NAT_PUNCH', (target_ip, target_port))
                time.sleep(0.2)
            
            # Tentar receber confirmação
            try:
                data, addr = s.recvfrom(1024)
                if data == b'NAT_PUNCH_ACK':
                    logger.info(f"Hole punching bem-sucedido para {target_address}")
                    return True
            except socket.timeout:
                logger.warning(f"Timeout ao esperar confirmação de {target_address}")
            
            return False
            
        except Exception as e:
            logger.error(f"Erro ao realizar hole punching: {e}")
            return False
        finally:
            s.close()
    
    def listen_for_punch(self, port, timeout=30):
        """
        Escuta por tentativas de hole punching.
        
        Args:
            port: Porta local para escutar
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            tuple: (sucesso, endereço do remetente)
        """
        try:
            # Criar socket UDP e associar à porta
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(timeout)
            s.bind(('0.0.0.0', port))
            
            logger.info(f"Escutando por hole punching na porta {port}")
            
            # Esperar por pacote de hole punching
            data, addr = s.recvfrom(1024)
            
            # Se recebeu o pacote correto, enviar confirmação
            if data == b'NAT_PUNCH':
                s.sendto(b'NAT_PUNCH_ACK', addr)
                logger.info(f"Hole punching recebido de {addr}")
                return True, f"{addr[0]}:{addr[1]}"
            
            return False, None
            
        except socket.timeout:
            logger.warning(f"Timeout ao esperar por hole punching")
            return False, None
        except Exception as e:
            logger.error(f"Erro ao escutar por hole punching: {e}")
            return False, None
        finally:
            s.close()
    
    def request_relay(self, source_id, target_id):
        """
        Solicita ao servidor de relay para ajudar na conexão quando
        a conexão direta falha.
        
        Args:
            source_id: ID do cliente de origem
            target_id: ID do cliente alvo
            
        Returns:
            bool: Sucesso da solicitação
        """
        if not self.relay_server:
            logger.error("Servidor de relay não configurado")
            return False
            
        try:
            # Solicitar relay ao servidor
            response = requests.post(
                f"{self.relay_server}/relay",
                json={
                    "source_id": source_id,
                    "target_id": target_id
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    relay_token = data.get("relay_token")
                    logger.info(f"Relay estabelecido com token: {relay_token}")
                    return True, relay_token
            
            logger.warning(f"Falha ao solicitar relay: {response.text}")
            return False, None
            
        except Exception as e:
            logger.error(f"Erro ao solicitar relay: {e}")
            return False, None
    
    @staticmethod
    def check_direct_connectivity(target_address, timeout=3):
        """
        Verifica se é possível estabelecer conexão direta com o alvo.
        
        Args:
            target_address: Endereço do alvo (IP:porta)
            timeout: Tempo máximo de espera em segundos
            
        Returns:
            bool: Sucesso da conexão
        """
        try:
            # Extrair IP e porta do alvo
            target_ip, target_port_str = target_address.split(':')
            target_port = int(target_port_str)
            
            # Tentar estabelecer conexão TCP
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            result = s.connect_ex((target_ip, target_port))
            
            if result == 0:
                logger.info(f"Conexão direta possível com {target_address}")
                return True
            else:
                logger.warning(f"Não foi possível conectar diretamente a {target_address}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao verificar conectividade: {e}")
            return False
        finally:
            s.close() 