import socket
import multiprocessing
import struct
import time
 

def ROAClient

def UDPsend

def timeTrig(cfg):
    
    period = 1
    
    while 1 :
    	if cfg.poll():
    		period = cfg.recv()
        time.sleep(period)


def ROAConfig(ROAcfgP, ROAmsgQ):

	DFT_FPGA_SOCK = ('10.10.1.100',13108)
	FPGA_SOCK = ('10.10.1.102',3202)
	OMLISTEN_SOCK = ('10.10.1.2',3201)

  	trigPeriodC, trigPeriodP = multiprocessing.Pipe(duplex = False)
  	trigProc = multiprocessing.Process(target=timeTrig, args=(trigPeriodC,))

  	trigProc.start
  	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # UDP
  	sock.bind(PC_SOCK)
  	sock.listen(1)
  	moa_conn,moa_addr = sock.accept()

	while 1:





	UDP_IP
	UDP_PORT
	MESSAGE="#CFG"
    MESSAGE += struct.pack("!I",0x0000050B)       	#Settings
    MESSAGE += struct.pack("!BH",0x00,10000) 	#Superframe period
    MESSAGE += struct.pack("!BH",0x00,8650) 	#TX start
    MESSAGE += struct.pack("!BH",0x00,9450) 	#TX end
    MESSAGE += struct.pack("!BH",0x00,0) 	#RX start
    MESSAGE += struct.pack("!BH",0x00,8300)  	#RX end
    MESSAGE += struct.pack("!BBB",0x75,0x00,128)	#AGC response(4) + HV level(12) + Preamble(8)
    MESSAGE += struct.pack("!BB",symrate,0x00)	#TX symbol rate + carrier rate
    MESSAGE += struct.pack("!BB",symrate,0x00) 	#RX symbol rate + carrier rate
    MESSAGE += struct.pack("!I",0x00F44010)     #Capture

    sock = socket.socket( socket.AF_INET, # Internet
                          socket.SOCK_DGRAM ) # UDP

    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))

    print "Config message sent to ", UDP_IP

def ROAStatServer



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
 

