import time
import errno
import socket
import tornado.ioloop

from tornado_dns.resolv import *
from tornado_dns.dns import *

class _errors(object):

    _codes = [
        (1, 'TIMEOUT', 'The query timed out'),
        (2, 'NO_NAMESERVERS', 'No nameserver was available to fulfil the request'),
        # range 100-199 reserved for dns error
        (100, 'DNS_ERROR', 'Nameserver cannot response the request successfully dur to other errors'),
        (101, 'DNS_SERVER_FAILED', 'Name server was unable to process the query due to an internal problem'),
        (102, 'DOMAIN_NOT_EXIST', 'Requested domain does not exist'),
    ]

    def __init__(self):
        self._descriptions = {}
        for num, name, description in self._codes:
            setattr(self, name, num)
            self._descriptions[num] = (name, description)

    def describe(self, num):
        return '%s: %s' % self._descriptions[num]

errors = _errors()

def invoke_errback(errback, code):
    if errback is not None:
        errback(code)

def get_socket(errback, server):
    if server is None:
        # always use the first configured nameserver
        servers = get_nameservers()
        if not servers:
            invoke_errback(errback, errors.NO_NAMESERVERS)
            return
        server = servers[0]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    return server, sock
    

def lookup(name, callback, errback=None, timeout=None, server=None):
    io_loop = tornado.ioloop.IOLoop.instance()
    server, sock = get_socket(errback, server)
    timeout_obj = None
    query = DNSPacket.create_a_question(name)

    def read_response(fd, events):
        # cancel the timeout
        if timeout_obj:
            io_loop.remove_timeout(timeout_obj)

        try:
            data, addr = sock.recvfrom(1500)
        except socket.error, e:
            # tornado lied to us??
            if e.errno == errno.EAGAIN:
                io_loop.remove_handler(fd)
                io_loop.add_handler(fd, read_response, io_loop.READ)
                return
            raise
        try:
            response = DNSPacket.from_wire(data)
            callback(response.get_answer_names())
        except ParseError as e:
            try:
                if e._rcode == 2:
                    errback(errors.DNS_SERVER_FAILED)
                elif e._rcode == 3:
                    errback(errors.DOMAIN_NOT_EXIST)
                else:
                    errback(errors.DNS_ERROR)
            except AttributeError:
                errback(errors.DNS_ERROR)
        io_loop.remove_handler(fd)


    def send_query(fd, events):
        sock.sendto(query.to_wire(), (server, 53))
        io_loop.remove_handler(fd)
        io_loop.add_handler(fd, read_response, io_loop.READ)

    def do_timeout():
        io_loop.remove_handler(sock.fileno())
        invoke_errback(errback, errors.TIMEOUT)

    io_loop.add_handler(sock.fileno(), send_query, io_loop.WRITE)
    if timeout:
        timeout_obj = io_loop.add_timeout(time.time() + timeout / 1000.0, do_timeout)
