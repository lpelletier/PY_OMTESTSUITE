import socket
import struct

def sendInitPkt(OMCFG_DICT): 

for i in IP:
...     hex(int(i))[2:].zfill(2)


#INITIAL SETTINGS
INIT_IP="192.168.1.100"
INIT_PORT=13108

#ARMADEUS SETTINGS
ARMA_MAC1=0x32A7D885
ARMA_MAC2=0x6ABF

#FPGA SETTINGS
FPGA_MAC1=0x46504741
FPGA_MAC2=0x3032

MESSAGE="#INI"

MESSAGE += struct.pack("!H", 0x0001) #RESET
MESSAGE += struct.pack("!IH",FPGA_MAC1,FPGA_MAC2)
MESSAGE += struct.pack("!BBBBH",FPGA_IP,FPGA_PORT)
MESSAGE += struct.pack("!IH",ARMA_MAC1,ARMA_MAC2)
MESSAGE += struct.pack("!BBBBH",ARMA_IP,ARMA_PORT)

sock = socket.socket( socket.AF_INET, # Internet
                      socket.SOCK_DGRAM ) # UDP

sock.sendto(MESSAGE, (INIT_IP, INIT_PORT))

print "Init Message sent to ",INIT_IP
