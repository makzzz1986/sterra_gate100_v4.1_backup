# -*- coding: utf-8 -*-

# for SSH
import paramiko
import time
import os
import sys
import datetime
import re
import base64


# writing to log
class to_log:
    log_file = open(sys.path[0] + '/main.log', 'a')

    def wr(self, string='', printer=False):
        # if True - output to console
        if printer is True:
            print string
      
        # writing to file date, time and message
        self.log_file.write(str(datetime.date.today()) + ' ' + str(datetime.datetime.now().time()) + ' --- ' + string + '\n')
        self.log_file.flush()

    def close(self):
        self.log_file.close()

    def flush(self):
        self.log_file.flush()


# script location
current_folder = sys.path[0]
# date
today = str(datetime.date.today())
# account name and passwords
user = 'root'
password = 'password'
en_pass = 'enable_password'
port = 22
# folder for backups
backup_folder = current_folder+'/backups/'
# list of hosts
list_file = current_folder + '/targets.txt'
# creating folder named of today
if not os.path.exists(backup_folder + today + '/'):
    os.makedirs(backup_folder + today + '/')

# file with results of scripts work
hosts_result = []

# open file with list of hosts
try:
    with open(list_file, 'r') as azs:
        log = to_log()
        log.wr('Script started!!!', True)

        # new line with host group, name, IP
        for line in azs.readlines():
            line = line.strip().split(',')

            # find group of host
            host_group = line[0]
            hosts_result.append(host_group)

            # creating folder of group if not exists
            if not os.path.exists(backup_folder + today + '/Gate100/' + host_group):
                os.makedirs(backup_folder + today + '/Gate100/' + host_group)

            # IP
            host = line[2]
            # hostname
            host_name = line[1]

            # checking existance of host by ping, 3 seconds timeout
            ping_response = os.system('ping -c 1 -w 3 ' + host + ' > /dev/null')

            # if S-terra gate answered
            if ping_response == 0:

                # creating instance of ssh connection
                client = paramiko.SSHClient()
                # adding RSA key to system database
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                try:
                    # connectng to host with ours account params
                    client.connect(hostname=host, username=user, password=password, port=port) 
                    channel = client.invoke_shell()
                    time.sleep(1)
                    log.wr('SSH connection opened')
                    gate_answer = ''
                    hostname = ''

                    try:
                        # enters to cisco-like interface
                        channel.send('cs_console\n')
                        time.sleep(0.1)

                        # enters to privileged mode 
                        channel.send('en\n'+en_pass+'\n')
                        time.sleep(0.1)

                        # write configuration to plain-text file on HDD and agreed of file name and rewriting
                        channel.send('copy running-config file:running-config.txt\n')
                        time.sleep(0.1)
                        channel.send('\n')
                        time.sleep(0.1)
                        channel.send('\n')
                        time.sleep(0.1)


                        # exit to bash
                        channel.send('exit\n')
                        time.sleep(0.5)

                        try:
                            # creating instance of SFTP
                            transport = paramiko.Transport(host, port)
                            # connecting with ours login/password
                            transport.connect(username=user, password=password)
                            sftp = paramiko.SFTPClient.from_transport(transport)
                            time.sleep(1)
                            log.wr('SFTP connection opened')
                            # creating folder with hostname
                            backup_host = backup_folder + today + '/Gate100/' + host_group + '/' + str(host_name) + '/'
                            if not os.path.exists(backup_host):
                                os.makedirs(backup_host)

                            # download cisco-like configuration
                            sftp.get('/var/cspvpn/running-config.txt', backup_host + '/running-config.txt')
                            time.sleep(0.1)
                            # download interfaces configuration
                            sftp.get('/etc/network/interfaces', backup_host + '/interfaces')
                            time.sleep(0.1)
                            # download cisco-like aliases of linux interfaces
                            sftp.get('/etc/ifaliases.cf', backup_host + '/ifaliases.cf')
                            time.sleep(0.1)
                            # download dhcpd.conf 
                            sftp.get('/etc/dhcp/dhcpd.conf', backup_host + '/dhcpd.conf')
                            time.sleep(0.1)
                            # download licenses
                            sftp.get('/opt/VPNagent/bin/agent.lic', backup_host + 'agent.lic')
                            time.sleep(0.1)
                            # if you need to download another files, just add here
                            # sftp.get('', backup_host + '')
                            #          ^^                ^^ - local file
                            #           --------------------- remote file
                            # time.sleep(0.1)
                            sftp.close()
                            transport.close()
                            hosts_result.append(host + ' backuped!')

                        # if something went wrong with SFTP connection
                        except Exception as e:
                            hosts_result.append(host + str(e))
                            log.wr('! Some problems with host ' + host, True)
                            log.wr('! Detail: ' + str(e), True)

                        finally:
                            # closing SFTP connection in any way
                            sftp.close()
                            transport.close()

                    # if something went wrong with SSH connection
                    except Exception as e:
                        hosts_result.append(host + str(e))
                        log.wr('! Some problems with host ' + host, True)
                        log.wr('! Detail: ' + str(e), True)

                    finally:
                        # closing SSH connection in any way
                        channel.close()
                        client.close()
                        # print 'Connection closed!'



                # if password wrong
                except paramiko.ssh_exception.AuthenticationException:
                    hosts_result.append(host + ' login or pass incorrect')
                    log.wr('login or pass incorrect with ' + host, True)

                # something went wrong
                except Exception as e:
                    hosts_result.append(host + str(e))
                    log.wr('! Some problems with host ' + host, True)
                    log.wr('! Detail: ' + str(e), True)

            # host didn't response on ping
            else:
                hosts_result.append(host + ' not pinged')

except Exception as e:
    log.wr('! Something wrong with targets.txt file!')
    log.wr('! Detail: ' + str(e))

# writing result of backup hosts
log.wr('Writing result.txt, all hosts = ' + str(len(hosts_result)))
with open(backup_folder + today + '/Gate100/' + 'result.txt', 'w') as result_file:
    for line in hosts_result:
        result_file.write(line + '\n')

log.wr('Script ENDS !!!', True)
log.close()

