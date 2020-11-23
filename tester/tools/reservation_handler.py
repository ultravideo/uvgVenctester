import datetime
import socket
import requests

from tester.core.singleton import Singleton
from tester import console_log


class ReservationException(Exception):
    pass


class ReservationHandler(metaclass=Singleton):

    def __init__(self, reservation_ip, port, name="Venctester", to_reserve_ip=None):
        self.RESERVATION_SERVER_IP = reservation_ip
        self.RESERVATION_SERVER_PORT = port
        self.RESERVATION_SERVER_URL = f'http://{self.RESERVATION_SERVER_IP}:{self.RESERVATION_SERVER_PORT}'

        # Here's some black magic. Tries to connect to reservation server and selects the ip from the interface that
        # made the connection. socket.gethostname() returns only last interface, which could be loop-back.
        try:
            self.SELF_IP = to_reserve_ip or \
                           [(s.connect((self.RESERVATION_SERVER_IP, int(self.RESERVATION_SERVER_PORT))),
                             s.getsockname()[0],
                             s.close()) for s in [socket.socket(socket.AF_INET, socket.SOCK_DGRAM)]][0][1]

            self.RESERVER_NAME = name

            self.SERVER_NAME, self.SERVER_ROW = self.__getSelfNameAndRow()
            console_log.info('Reservation handler:')
            console_log.info(' Reservation server URL: ' + self.RESERVATION_SERVER_URL)
            console_log.info(' Self IP: ' + str(self.SELF_IP))
            console_log.info(' Identified as: ' + str(self.SERVER_NAME))
            console_log.info('')
        except Exception as e:
            console_log.error("Error when trying to contact reservation server:\n" + str(e))
            self.SERVER_NAME = None

    def reserve_server(self, *, time_h=0, time_m=0):
        if self.SERVER_NAME is None:
            return

        console_log.info('Reserving {} for {} hours and {} minutes...'.format(self.SERVER_NAME, time_h, time_m))

        if 'status off' in self.SERVER_ROW:
            reserver = self.__grabHtmlContent(self.SERVER_ROW, '<td class="resby">', '</td>')
            if reserver == self.RESERVER_NAME:
                return
            timestamp = self.__grabHtmlContent(self.SERVER_ROW, '<td class="resun">', '</td>')
            raise ReservationException('Server is reserved by "{reserver}" until "{time}"'.format(
                reserver=reserver,
                time=timestamp)
            )

        self.__serverReservation(time_h=time_h, time_m=time_m)

    def free_server(self):
        if self.SERVER_NAME is None:
            return

        console_log.info('Freeing {}.'.format(self.SERVER_NAME))

        self.__serverReservation(time_h=0, time_m=0)

    def __getSelfNameAndRow(self):
        r = requests.get(self.RESERVATION_SERVER_URL)

        ip_tag = '<a href="rdp://{ip}/">'.format(ip=self.SELF_IP)

        if not ip_tag in r.text:
            return None, None

        begin = r.text.find(ip_tag)
        begin = r.text[:begin].rfind('<tr>')
        end = r.text[begin:].find('</tr>')
        row = r.text[begin:begin + end + len('</tr>')]

        name = self.__grabHtmlContent(row, '<td class="server">', '</td>')

        return name, row

    def __grabHtmlContent(self, line, s_tag, e_tag):
        begin = line.find(s_tag) + len(s_tag)
        end = line[begin:].find(e_tag)
        return line[begin:begin + end]

    def __serverReservation(self, *, time_h=0, time_m=0):
        header = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        time = int(datetime.datetime.now().timestamp()) + 60 * time_m + 60 * 60 * time_h
        data = {
            'name': self.SERVER_NAME,
            'user': self.RESERVER_NAME,
            'time': time,
        }
        requests.post(self.RESERVATION_SERVER_URL, headers=header, data=data)
