import asyncio
import json
import threading

import websockets


class WebSocketClient:
    def __init__(self, uri, status_callback, message_queue):
        self._uri = uri
        self._status_callback = status_callback
        self._message_queue = message_queue
        self._conn = None
        self._thread = None
        self._send_queue = asyncio.Queue()
        self._stop_event = asyncio.Event()
        self._connected = False
        self._loop = None

    def connect(self):
        if self._thread is not None and self._thread.is_alive():
            print("WebSocket thread já está rodando.")
            return
        
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_async_loop, daemon=True)
        self._thread.start()

    def _run_async_loop(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._main_loop())
        except Exception as e:
            print(f"Erro fatal no loop async do WebSocket: {e}")
            self._connected = False
            self._status_callback("Error")
        finally:
             if self._loop:
                self._loop.close()
             self._connected = False
             print("Loop async do WebSocket finalizado.")

    async def _main_loop(self):
        while not self._stop_event.is_set():
            try:
                self._status_callback("Connecting...")
                async with websockets.connect(self._uri) as websocket:
                    self._conn = websocket
                    self._connected = True
                    self._status_callback("Connected")
                    print(f"Conectado ao WebSocket em {self._uri}")

                    # Iniciar tarefas concorrentes para enviar e receber
                    recv_task = asyncio.create_task(self._recv_loop())
                    send_task = asyncio.create_task(self._send_loop())
                    # Corrigir erro "Passing coroutines is forbidden"
                    stop_wait_task = asyncio.create_task(self._stop_event.wait()) 
                    done, pending = await asyncio.wait(
                        [recv_task, send_task, stop_wait_task], # Usar a task criada
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    # Cancelar tarefas pendentes ao sair
                    for task in pending:
                        task.cancel()
                    
                    # Verificar se saímos por causa do stop_event
                    if self._stop_event.is_set():
                         print("Stop event set, saindo do main loop.")
                         break # Sai do loop while externo
            
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK) as e:
                print(f"WebSocket desconectado: {e.code} {e.reason}")
            except ConnectionRefusedError:
                print("Erro de conexão WebSocket: Conexão recusada.")
            except OSError as e: # Captura erros como [WinError 10049] ou [Errno 11001] getaddrinfo failed
                print(f"Erro de conexão WebSocket (OS): {e}")
            except Exception as e:
                print(f"Erro inesperado no main_loop WebSocket: {e}")
            finally:
                self._conn = None
                self._connected = False
                if not self._stop_event.is_set():
                    self._status_callback("Disconnected")
                    print("Tentando reconectar em 5 segundos...")
                    await asyncio.sleep(5)
                else:
                    print("Não tentando reconectar, stop event ativo.")
                    self._status_callback("Stopped")

    async def _recv_loop(self):
        while self._connected and not self._stop_event.is_set():
            try:
                message_str = await self._conn.recv()
                try:
                    message_dict = json.loads(message_str)
                    self._message_queue.put(message_dict)
                except json.JSONDecodeError:
                    print(f"Erro: Recebido JSON inválido do WebSocket: {message_str}")
            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                print("Recv loop: Conexão fechada.")
                self._connected = False
                break
            except asyncio.CancelledError:
                print("Recv loop cancelado.")
                break
            except Exception as e:
                print(f"Erro no recv_loop WebSocket: {e}")
                self._connected = False
                break
        print("Recv loop finalizado.")

    async def _send_loop(self):
        while self._connected and not self._stop_event.is_set():
            try:
                # Espera por uma mensagem na fila ou pelo stop event
                get_task = asyncio.create_task(self._send_queue.get())
                stop_task = asyncio.create_task(self._stop_event.wait())
                done, pending = await asyncio.wait(
                    [get_task, stop_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if stop_task in done:
                    get_task.cancel() # Cancela a espera da fila se paramos
                    print("Send loop: Stop event recebido.")
                    break

                if get_task in done:
                    message_dict = get_task.result()
                    message_str = json.dumps(message_dict)
                    await self._conn.send(message_str)
                    self._send_queue.task_done()
                else: # stop_task must be done
                     get_task.cancel()
                     break

            except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosedOK):
                print("Send loop: Conexão fechada.")
                self._connected = False
                break
            except asyncio.CancelledError:
                print("Send loop cancelado.")
                break
            except Exception as e:
                print(f"Erro no send_loop WebSocket: {e}")
                self._connected = False
                break
        print("Send loop finalizado.")

    def send(self, message_dict):
        if not self._connected:
            print("Erro: Tentativa de enviar mensagem WebSocket sem conexão.")
            return False
        try:
            # Adiciona à fila de envio (que será processada pelo _send_loop)
            if self._loop and self._loop.is_running():
                 asyncio.run_coroutine_threadsafe(self._send_queue.put(message_dict), self._loop)
                 return True
            else:
                 print("Erro: Loop async não está rodando para enfileirar mensagem.")
                 return False
        except Exception as e:
             print(f"Erro ao enfileirar mensagem para envio: {e}")
             return False

    def is_connected(self):
        return self._connected

    def close(self):
        print("Solicitando fechamento do WebSocket...")
        self._stop_event.set() # Sinaliza para as tarefas pararem
        # Tentar acordar o _send_loop se ele estiver esperando na fila
        if self._loop and self._loop.is_running():
             asyncio.run_coroutine_threadsafe(self._send_queue.put(None), self._loop) # Envia None para desbloquear

        if self._thread is not None and self._thread.is_alive():
            print("Aguardando thread WebSocket finalizar...")
            self._thread.join(timeout=5) # Espera um pouco pela thread
            if self._thread.is_alive():
                print("Thread WebSocket não finalizou a tempo.")
        self._thread = None
        print("Fechamento do WebSocket solicitado.")
