OMCFG_DICT = {'OM_IP' : "0.0.0.0", 'OM_PORT' : 0, 'ARM_IP' : "0.0.0.0", 'ARM_PORT' : 0} 

#Parse om_ipaddr.cfg in directory
with open('./om_ipaddr.cfg','r+') as CONFIG_FILE:
   for line in CONFIG_FILE:
       words=line.split()
       
       try:
           if words[0] == "OM_IPDATA":
               OMCFG_DICT['OM_IP'] = words[2]
               OMCFG_DICT['OM_PORT'] = words[3]
           elif words[0] == "ARM_IPDATA":
               OMCFG_DICT['ARM_IP'] = words[2]
               OMCFG_DICT['ARM_PORT'] = words[3]
       except IndexError:
           print "Invalid Index"



