#!/usr/bin/python

from struct import unpack
from socket import *

#INITIAL FPGA SOCKET
UDP_IP='10.10.1.2'
UDP_PORT=3201
data = ''
sock = socket( AF_INET, # Internet
	           SOCK_DGRAM ) # UDP

print 'Ready'

sock.bind((UDP_IP, UDP_PORT))

while 1:

	data = sock.recv(63)

	if data[0:4] == '#STA':
		print 'Received STA'
		print '   Transmitted ', unpack('!I', data[46:50]), ' bytes'
	elif data[0:4] == '#EMS':
		print 'Received EMS, Ignoring...'


