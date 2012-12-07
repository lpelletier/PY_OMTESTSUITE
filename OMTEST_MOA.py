from socket import *      #import the socket library
from struct import unpack
 
PORT = 5568    #arbitrary port not currently in use
PCADDR = ('192.168.2.4',5566)    #we need a tuple for the address
received = 0
recv_totalpkt = 0
recv_pktsize = 0



## now we create a new socket object (serv)
## see the python docs for more information on the socket types/flags
clt = socket( AF_INET,SOCK_STREAM)
clt.connect(PCADDR)

recv_totalpkt, recv_pktsize = unpack('!II', clt.recv(8))
print recv_totalpkt
print recv_pktsize

for i in xrange(recv_totalpkt):
	DATA = clt.recv(recv_pktsize)
	received += 1470

print received
clt.close()
print 'Done'
 

