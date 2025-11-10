from mininet.topo import Topo
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.link import TCLink
from mininet.cli import CLI
from mininet.log import setLogLevel

class MyTopo(Topo):
    def build(self):
        s1 = self.addSwitch('s1')
        h1 = self.addHost('h1',   ip='10.0.0.1/24')
        h2 = self.addHost('h2',   ip='10.0.0.2/24')
        web1 = self.addHost('web1', ip='10.0.0.3/24')
        nfv1 = self.addHost('nfv1', ip='10.0.0.254/24')
        self.addLink(h1, s1); self.addLink(h2, s1)
        self.addLink(web1, s1); self.addLink(nfv1, s1)

def _mirror_to_nfv(net):
    s1, web1, nfv1 = net.get('s1','web1','nfv1')
    wp = s1.ports[web1.defaultIntf()]
    np = s1.ports[nfv1.defaultIntf()]
    s1.cmd('ovs-vsctl -- clear Bridge s1 mirrors')
    s1.cmd(f'ovs-vsctl -- --id=@p get port s1-eth{wp} '
           f'-- --id=@o get port s1-eth{np} '
           f'-- --id=@m create Mirror name=mir-http select-dst-port=@p output-port=@o '
           f'-- set Bridge s1 mirrors=@m')

def run():
    topo = MyTopo()
    net = Mininet(topo=topo, controller=None, switch=OVSSwitch,
                  link=TCLink, autoSetMacs=True, autoStaticArp=True)
    net.addController(RemoteController('c0', ip='127.0.0.1', port=6633))
    net.start()

    for name in ['h1','h2','web1','nfv1']:
        net.get(name).cmd('ip route add default via 10.0.0.254 || true')

    net.get('web1').cmd('nohup python3 -m http.server 80 >/tmp/web1.out 2>&1 &')
    _mirror_to_nfv(net)

    print('*** Listo. En Mininet: nfv1 python3 ~/t3-sdn/nfv/http_monitor.py &')
    print('*** Prueba: h1 curl -I http://10.0.0.3  (bloqueado) ; h2 curl -I http://10.0.0.3 (OK)')
    CLI(net); net.stop()

if __name__ == '__main__':
    setLogLevel('info'); run()
