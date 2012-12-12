#!/usr/bin/python
from multiprocessing import Process
from sys import argv
from struct import pack
from socket import *
from subprocess import call, PIPE
from time import sleep

class ROAConfig(Process)

	EMITTER_ID = '24'
	testing = 0
	om_settings = {'bitrate': 3, 'fec': 1, 'emit_pwr': '0', 'emit_dim': '0'}
	om_prevstatus = {'tx_bytes': 0, 'corrected': 0, 'ncorrected': 0, 'bad_CRC':0, 'flowproblem': 0}


	def __init__(self, bitrate, fec, emit_pwr, emit_dim):
		self.om_settings['bitrate'] = bitrate
		self.om_settings['fec'] = fec
		self.om_settings['emit_pwr'] = emit_pwr
		self.om_settings['emit_dim'] = emit_dim
		self.testing = 0


	def runTest(self):
		self.testing = 1


	def stopTest(self):
		self.testing = 0


	def resetOM(self):
		loadFpga = call(['/root/load_fpga_WHOI', '/root/om3x_spartan6_b27.bit'], stdout=PIPE)
		self.INIPktGen()
		sleep(0.2)
		self.CFGPktGen()
		self.EMCPktGen('24','0','0')


	def __INIPktGen(self): 

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

		sock = socket( AF_INET, SOCK_DGRAM ) # UDP
		sock.sendto(MESSAGE, (INIT_IP, INIT_PORT))
		sock.close()


	def CFGPktGen(self): 

	    #CONFIGURATION SOCKET
	    UDP_IP="10.10.1.102"
	    UDP_PORT=3202

	    #Modulation settings
	    PREAMBLE = 512  #at 2*symbol rate

	    MESSAGE="#CFG"
	    MESSAGE += pack("!HBB",0x0000,(self.om_settings['fec']*5),0x0B)  #Settings
	    MESSAGE += pack("!BH",0x00,10000) 	#Superframe period
	    MESSAGE += pack("!BH",0x00,8650) 	#TX start
	    MESSAGE += pack("!BH",0x00,9450) 	#TX end
	    MESSAGE += pack("!BH",0x00,0) 	#RX start
	    MESSAGE += pack("!BH",0x00,8300)  	#RX end
	    MESSAGE += pack("!BBB",0x75,0x00,PREAMBLE/4)	#AGC response(4) + HV level(12) + Preamble(8)
	    MESSAGE += pack("!BB",self.om_settings['bitrate'],0x00)	#TX symbol rate + carrier rate
	    MESSAGE += pack("!BB",self.om_settings['bitrate'],0x00) 	#RX symbol rate + carrier rate
	    MESSAGE += pack("!I",0x000F8001)     #Capture

	    sock = socket( AF_INET, SOCK_DGRAM )
	    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
	    sock.close


	def EMCPktGen(self): 

	    #CONFIGURATION SOCKET
	    UDP_IP="10.10.1.102"
	    UDP_PORT=3202

	    MESSAGE="#EMC"
	    MESSAGE += pack("!H",0)
	    MESSAGE += pack("!cccc",self.EMITTER_ID[0],
	    						self.EMITTER_ID[1],
	    						self.om_settings['emit_pwr'],
	    						self.om_settings['emit_dim'])	

	    sock = socket( AF_INET, SOCK_DGRAM )
	    sock.sendto(MESSAGE, (UDP_IP, UDP_PORT))
	    sock.close



	def ROAStatus(ROAConfig): 

		#INITIAL FPGA SOCKET
		UDP_IP='10.10.1.2'
		UDP_PORT=3201

		sock = socket( AF_INET, # Internet
			           SOCK_DGRAM ) # UDP

		sock.bind((UDP_IP, UDP_PORT))

		while 1:

			while data[0:4] != '#STA':
				data[0:4] = data[1:4] + sock.recv(1)
			

			print 'received ', data[0:4]




