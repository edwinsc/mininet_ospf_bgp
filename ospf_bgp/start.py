#!/usr/bin/env python

from mininet.topo import Topo
from mininet.net import Mininet
from mininet.log import lg, info, setLogLevel
from mininet.util import dumpNodeConnections, quietRun, moveIntf
from mininet.cli import CLI
from mininet.node import Switch, OVSKernelSwitch

from subprocess import Popen, PIPE, check_output
from time import sleep, time
from multiprocessing import Process
from argparse import ArgumentParser

import sys
import os
import termcolor as T
import time

setLogLevel('info')

parser = ArgumentParser("Configure 1 OSPF+BGP AS and 2 BGP only AS in Mininet.")
parser.add_argument('--sleep', default=3, type=int)
args = parser.parse_args()

def log(s, col="green"):
    print T.colored(s, col)


class Router(Switch):
    """Defines a new router that is inside a network namespace so that the
    individual routing entries don't collide.

    """
    ID = 0
    def __init__(self, name, **kwargs):
        kwargs['inNamespace'] = True
        Switch.__init__(self, name, **kwargs)
        Router.ID += 1
        self.switch_id = Router.ID

    @staticmethod
    def setup():
        return

    def start(self, controllers):
        pass

    def stop(self):
        self.deleteIntfs()

    def log(self, s, col="magenta"):
        print T.colored(s, col)


class SimpleTopo(Topo):
    def __init__(self):
        # Add default members to class.
        super(SimpleTopo, self ).__init__()
	num_hosts_per_router = 1 # The topology has one host per router
	routers = []
	hosts = []

	#AS10
	num_router = 5
	# create routers
        for i in xrange(num_router):
            router = self.addSwitch('r010_%d' % (i+1))
            routers.append(router)

        # add link between routers
        for i in xrange(num_router-1):
            self.addLink('r010_%d' % (i+1), 'r010_%d' % (i+2))
        self.addLink('r010_5', 'r010_1')
        
        # create and attach one host per router
	for i in xrange(num_router):
            router = 'r010_%d' % (i+1)
            for j in xrange(num_hosts_per_router):
                hostname = 'h010_%d%d' % (i+1, j+1)
                host = self.addNode(hostname)
                hosts.append(host)
                self.addLink(router, host)

        #routers AS100 and AS200 and BGP links
	router = self.addSwitch('r100_1')
        routers.append(router)
        router = self.addSwitch('r200_1')
        routers.append(router)
        self.addLink('r010_1', 'r100_1')
        self.addLink('r010_1', 'r200_1')
        self.addLink('r100_1', 'r200_1')
	
	#AS100 hosts
        router = 'r100_1'
        for j in xrange(num_hosts_per_router):
            hostname = 'h100_1%d' % (j+1)
            host = self.addNode(hostname)
            hosts.append(host)
            self.addLink(router, host)

	#AS200 hosts
        router = 'r200_1'
        for j in xrange(num_hosts_per_router):
            hostname = 'h200_1%d' % (j+1)
            host = self.addNode(hostname)
            hosts.append(host)
            self.addLink(router, host)

        return

# Define host IP
def getIP(hostname):
    if hostname == "h010_11":
        ip = '10.1.0.2/24'
    elif hostname == "h010_21":
        ip = '10.2.0.2/24'
    elif hostname == "h010_31":
        ip = '10.3.0.2/24'
    elif hostname == "h010_41":
        ip = '10.4.0.2/24'
    elif hostname == "h010_51":
        ip = '10.5.0.2/24'
    elif hostname == "h100_11":
        ip = '100.1.0.2/24'
    elif hostname == "h200_11":
        ip = '200.1.0.2/24'
    else:
        log("WARNING: No IP was set for %s. Your netowork will probably not work correctly." % hostname)
        ip = ''
    return ip

# Define host Gateway
def getGateway(hostname):
    if hostname == "h010_11":
        gw = '10.1.0.1'
    elif hostname == "h010_21":
        gw = '10.2.0.1'
    elif hostname == "h010_31":
        gw = '10.3.0.1'
    elif hostname == "h010_41":
        gw = '10.4.0.1'
    elif hostname == "h010_51":
        gw = '10.5.0.1'
    elif hostname == "h100_11":
        gw = '100.1.0.1'
    elif hostname == "h200_11":
        gw = '200.1.0.1'
    else:
        gw = ''
    return gw

# Start the routing daemons
# When a I2RS daemon is ready add it to the routers you want it to run, probably run:
# router.cmd("/usr/lib/quagga/i2rsd -f conf/i2rsd-%s.conf -d -i /tmp/i2rsd-%s.pid > logs/%s-i2rsd-stdout 2>&1" % (router.name, router.name, router.name))
# router.waitOutput()
def startRouting(router):
    if router.name == "r010_1":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/ospfd -f conf/ospfd-%s.conf -d -i /tmp/ospfd-%s.pid > logs/%s-ospfd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        router.cmd("/usr/lib/quagga/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgpd-%s.pid > logs/%s-bgpd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and ospfd and bgpd on %s" % router.name)
    elif router.name == "r010_2":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/ospfd -f conf/ospfd-%s.conf -d -i /tmp/ospfd-%s.pid > logs/%s-ospfd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and ospfd on %s" % router.name)
    elif router.name == "r010_3":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/ospfd -f conf/ospfd-%s.conf -d -i /tmp/ospfd-%s.pid > logs/%s-ospfd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and ospfd on %s" % router.name)
    elif router.name == "r010_4":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/ospfd -f conf/ospfd-%s.conf -d -i /tmp/ospfd-%s.pid > logs/%s-ospfd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and ospfd on %s" % router.name)
    elif router.name == "r010_5":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/ospfd -f conf/ospfd-%s.conf -d -i /tmp/ospfd-%s.pid > logs/%s-ospfd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and ospfd on %s" % router.name)
    elif router.name == "r100_1":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgpd-%s.pid > logs/%s-bgpd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and bgpd on %s" % router.name)
    elif router.name == "r200_1":
        router.cmd("/usr/lib/quagga/zebra -f conf/zebra-%s.conf -d -i /tmp/zebra-%s.pid > logs/%s-zebra-stdout 2>&1" % (router.name, router.name, router.name))
        router.waitOutput()
        router.cmd("/usr/lib/quagga/bgpd -f conf/bgpd-%s.conf -d -i /tmp/bgpd-%s.pid > logs/%s-bgpd-stdout 2>&1" % (router.name, router.name, router.name), shell=True)
        router.waitOutput()
        log("Starting zebra and bgpd on %s" % router.name)
    else:
        log("WARNING: No routing deamon configured for %s." % (router.name))
    return

def main():
    os.system("rm -f /tmp/r*.log /tmp/r*.pid logs/*")
    os.system("mn -c >/dev/null 2>&1")
    os.system("killall -9 zebra bgpd ospfd > /dev/null 2>&1")

    net = Mininet(topo=SimpleTopo(), switch=Router)
    net.start()
    for router in net.switches:
        router.cmd("sysctl -w net.ipv4.ip_forward=1")
        router.waitOutput()

    log("Waiting %d seconds for sysctl changes to take effect..."
        % args.sleep)
    sleep(args.sleep)

    # initialize routing daemons
    for router in net.switches:
        startRouting(router)

    # set hosts IP and gateways
    for host in net.hosts:
#        using "ip cmd" leaves 10.0.0.x/8 ip on the interface of the hosts and 10.0.0.0/8 on the routing table
#        host.cmd("ip a add %s dev %s-eth0" % (getIP(host.name), host.name))
#        host.cmd("ip r add default via %s" % (getGateway(host.name)))
        host.cmd("ifconfig %s-eth0 %s" % (host.name, getIP(host.name)))
        host.cmd("route add default gw %s" % (getGateway(host.name)))

    CLI(net)
    net.stop()
    os.system("killall -9 zebra bgpd ospfd")

if __name__ == "__main__":
    main()
