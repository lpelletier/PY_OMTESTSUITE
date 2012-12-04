import socket
import struct

def sendFilePkt(SOCKET, WORK, TRIGGER): 

    INDEX = 0
    DELAY = float(PKT_SIZE_B * 8) / float(RATE_MB * 1024 * 1024)
    MESSAGE="#CFG"

    print DELAY

    #NETWORK INIT
    #UDP_IP = "10.10.1.3"
    #UDP_PORT = 4456

    #sock = socket.socket( socket.AF_INET, # Internet
                          #socket.SOCK_DGRAM ) # UDP



   #with open('./om_ipaddr.cfg','r+b') as CONFIG_FILE:
    #CONFIG_FILE.read

    #sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
