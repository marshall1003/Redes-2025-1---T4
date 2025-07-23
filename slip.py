class CamadaEnlace:
    ignore_checksum = False

    def __init__(self, linhas_seriais):
        """
        Inicia uma camada de enlace com um ou mais enlaces, cada um conectado
        a uma linha serial distinta. O argumento linhas_seriais é um dicionário
        no formato {ip_outra_ponta: linha_serial}.
        """
        self.enlaces = {}
        self.callback = None
        for ip_outra_ponta, linha_serial in linhas_seriais.items():
            enlace = Enlace(linha_serial)
            self.enlaces[ip_outra_ponta] = enlace
            enlace.registrar_recebedor(self._callback)

    def registrar_recebedor(self, callback):
        """
        Registra uma função para ser chamada quando dados vierem da camada de enlace
        """
        self.callback = callback

    def enviar(self, datagrama, next_hop):
        """
        Envia datagrama para next_hop (string no formato x.y.z.w).
        """
        self.enlaces[next_hop].enviar(datagrama)

    def _callback(self, datagrama):
        if self.callback:
            self.callback(datagrama)


class Enlace:
    SLIP_END = 0xC0
    SLIP_ESC = 0xDB
    SLIP_ESC_END = 0xDC
    SLIP_ESC_ESC = 0xDD

    def __init__(self, linha_serial):
        self.linha_serial = linha_serial
        self.linha_serial.registrar_recebedor(self.__raw_recv)
        self.callback = None
        self.buffer = bytearray()
        self.escaping = False  # Para lidar com escapes

    def registrar_recebedor(self, callback):
        self.callback = callback

    def enviar(self, datagrama):
        """
        Envia datagrama pela linha serial, utilizando SLIP.
        """
        quadro = bytearray()
        quadro.append(self.SLIP_END)  # Delimita início do quadro

        for byte in datagrama:
            if byte == self.SLIP_END:
                quadro += bytes([self.SLIP_ESC, self.SLIP_ESC_END])
            elif byte == self.SLIP_ESC:
                quadro += bytes([self.SLIP_ESC, self.SLIP_ESC_ESC])
            else:
                quadro.append(byte)

        quadro.append(self.SLIP_END)  # Delimita fim do quadro

        self.linha_serial.enviar(bytes(quadro))

    def __raw_recv(self, dados):
        """
        Reconstrói quadros SLIP a partir de dados recebidos da linha serial.
        """
        for byte in dados:
            if byte == self.SLIP_END:
                if len(self.buffer) > 0:
                    # Quadro completo montado, entrega o datagrama
                    if self.callback:
                        try:
                            self.callback(bytes(self.buffer))
                        except Exception:
                            import traceback
                            traceback.print_exc()
                        finally:
                            self.buffer.clear()  # Garante que o buffer seja esvaziado mesmo em caso de erro
                    else:
                        self.buffer.clear()

                else:
                    # Quadro vazio → ignora
                    continue
                self.escaping = False  # Reset estado de escape
            elif self.escaping:
                if byte == self.SLIP_ESC_END:
                    self.buffer.append(self.SLIP_END)
                elif byte == self.SLIP_ESC_ESC:
                    self.buffer.append(self.SLIP_ESC)
                else:
                    # Erro de escape → trata como byte normal
                    self.buffer.append(byte)
                self.escaping = False
            elif byte == self.SLIP_ESC:
                self.escaping = True
            else:
                self.buffer.append(byte)
