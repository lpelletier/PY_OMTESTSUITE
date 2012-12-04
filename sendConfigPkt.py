import socket
import struct

def sendConfigPkt(UDP_IP, UDP_PORT, SYMRATE): 

    MESSAGE="#CFG"

    #Scheduler settings
    SUPERFRAME = 10000 
    TXSTART = 8650
    TXEND = 9450
    RXSTART = 0
    RXEND = 8300

    #Modulation settings
    PREAMBLE = 512  #at 2*symbol rate

    MESSAGE += struct.pack("!I",0x00000501)       	#Settings
    MESSAGE += struct.pack("!BH",0x00,SUPERFRAME) 	#Superframe period
    MESSAGE += struct.pack("!BH",0x00,TXSTART) 	#TX start
    MESSAGE += struct.pack("!BH",0x00,TXEND) 	#TX end
    MESSAGE += struct.pack("!BH",0x00,RXSTART) 	#RX start
    MESSAGE += struct.pack("!BH",0x00,RXEND)  	#RX end
    MESSAGE += struct.pack("!BBB",0x75,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
    MESSAGE += struct.pack("!BB",SYMRATE,0x00)	#TX symbol rate + carrier rate
    MESSAGE += struct.pack("!BB",SYMRATE,0x00) 	#RX symbol rate + carrier rate
    MESSAGE += struct.pack("!I",0x00F44010)     #Capture

    sock = socket.socket( socket.AF_INET, # Internet
                          socket.SOCK_DGRAM ) # UDP

    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))

    print "Config message sent to ", UDP_IP