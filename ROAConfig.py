#!/usr/bin/python

from sys import argv
from struct import pack
from socket import *
from subprocess import call, PIPE
from time import sleep


def INIPktGen(): 

	#INITIAL FPGA SOCKET
	INIT_IP='10.10.1.100'
	INIT_PORT=13108

	#FPGA CONFIG
	FPGA_MAC1=0x12345678
	FPGA_MAC2=0x90AB
	FPGA_IP=0x0A0A0166
	FPGA_PORT=3202

	#ARMADEUS CONFIG
	ARMA_MAC1=0x32A7D885
	ARMA_MAC2=0x6ABF
	ARMA_IP=0x0A0A0102
	ARMA_PORT= 3201

	MESSAGE="#INI"
	MESSAGE += pack("!H", 0x0001) #RESET
	MESSAGE += pack("!IH",FPGA_MAC1,FPGA_MAC2)
	MESSAGE += pack("!IH",FPGA_IP,FPGA_PORT)
	MESSAGE += pack("!IH",ARMA_MAC1,ARMA_MAC2)
	MESSAGE += pack("!IH",ARMA_IP,ARMA_PORT)

	sock = socket( AF_INET, # Internet
		           SOCK_DGRAM ) # UDP

	sock.sendto(MESSAGE, (INIT_IP, INIT_PORT))
	sock.close()


def CFGPktGen(): 

    #CONFIGURATION SOCKET
    UDP_IP="10.10.1.102"
    UDP_PORT=3202

    #Modulation settings
    PREAMBLE = 512  #at 2*symbol rate
    SYMRATE = 4

    MESSAGE="#CFG"
    MESSAGE += pack("!I",0x0000050B)       	#Settings
    MESSAGE += pack("!BH",0x00,10000) 	#Superframe period
    MESSAGE += pack("!BH",0x00,8650) 	#TX start
    MESSAGE += pack("!BH",0x00,9450) 	#TX end
    MESSAGE += pack("!BH",0x00,0) 	#RX start
    MESSAGE += pack("!BH",0x00,8300)  	#RX end
    MESSAGE += pack("!BBB",0x75,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
    MESSAGE += pack("!BB",SYMRATE,0x00)	#TX symbol rate + carrier rate
    MESSAGE += pack("!BB",SYMRATE,0x00) 	#RX symbol rate + carrier rate
    MESSAGE += pack("!I",0x000F8001)     #Capture

    sock = socket( AF_INET, # Internet
                   SOCK_DGRAM ) # UDP

    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
    sock.close


def EMCPktGen(id,power,dim): 

    #CONFIGURATION SOCKET
    UDP_IP="10.10.1.102"
    UDP_PORT=3202

    MESSAGE="#EMC"
    MESSAGE += pack("!H",0)
    MESSAGE += pack("!cccc",id[0],id[1],power,dim)	

    sock = socket( AF_INET, # Internet
                   SOCK_DGRAM ) # UDP

    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
    sock.close


def statListen(): 

	#INITIAL FPGA SOCKET
	UDP_IP='10.10.1.2'
	UDP_PORT=3201

	sock = socket( AF_INET, # Internet
		           SOCK_DGRAM ) # UDP

	sock.bind((UDP_IP, UDP_PORT))

	while 1:

		data = sock.recv(63) 
		print 'received ', data[0:4]


def ROAConfig(cmd):
	
	if cmd == 'INI':
		loadFpga = call(['/root/load_fpga_WHOI', '/root/om3x_spartan6_b27.bit'], stdout=PIPE)
		INIPktGen()
		sleep(0.1)
		CFGPktGen()
		EMCPktGen('24','0','0')
		statListen()
	
	elif cmd == 'CFG':
		CFGPktGen()
		EMCPktGen('24','1','1')
		statListen()

if __name__ == "__main__":
    ROAConfig(argv[1])

