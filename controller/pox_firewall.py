from pox.core import core
import pox.openflow.libopenflow_01 as of

log = core.getLogger()

# Reglas: 6=TCP, 1=ICMP
FIREWALL_RULES = [
    {"nw_proto": 6, "tp_dst": 80, "nw_src": "10.0.0.1", "nw_dst": "10.0.0.3"},  # h1 HTTP -> web1 (bloqueado)
    {"nw_proto": 1, "nw_src": "10.0.0.2"},  # ICMP desde h2 (bloqueado)
]

class L2LearningFirewall(object):
    def __init__(self, connection):
        self.connection = connection
        self.mac_to_port = {}
        connection.addListeners(self)

        fm = of.ofp_flow_mod()
        fm.priority = 0
        fm.actions.append(of.ofp_action_output(port=of.OFPP_CONTROLLER))
        self.connection.send(fm)

    def _matches(self, packet, ipv4=None, tcp=None, icmp=None):
        for r in FIREWALL_RULES:
            ok = True
            if "nw_proto" in r and (ipv4 is None or ipv4.protocol != r["nw_proto"]): ok = False
            if ok and "tp_dst" in r and (tcp is None or tcp.dstport != r["tp_dst"]): ok = False
            if ok and "nw_src" in r and (ipv4 is None or str(ipv4.srcip) != r["nw_src"]): ok = False
            if ok and "nw_dst" in r and (ipv4 is None or str(ipv4.dstip) != r["nw_dst"]): ok = False
            if ok: return True
        return False

    def _learn_and_forward(self, packet, packet_in):
        self.mac_to_port[packet.src] = packet_in.in_port
        if packet.dst.is_multicast:
            self.connection.send(of.ofp_packet_out(data=packet_in,
                               action=of.ofp_action_output(port=of.OFPP_FLOOD)))
            return
        out_port = self.mac_to_port.get(packet.dst, of.OFPP_FLOOD)
        action = of.ofp_action_output(port=out_port)
        fm = of.ofp_flow_mod()
        fm.match = of.ofp_match.from_packet(packet, packet_in.in_port)
        fm.actions.append(action); fm.idle_timeout = 20
        self.connection.send(fm)
        self.connection.send(of.ofp_packet_out(data=packet_in, action=action))

    def _handle_PacketIn(self, event):
        p = event.parsed
        ipv4 = p.find('ipv4'); tcp = p.find('tcp'); icmp = p.find('icmp')
        if self._matches(p, ipv4=ipv4, tcp=tcp, icmp=icmp):
            fm = of.ofp_flow_mod()
            fm.match = of.ofp_match.from_packet(p, event.ofp.in_port)
            fm.priority = 2000; fm.idle_timeout = 60
            self.connection.send(fm)  # sin acciones => DROP
            log.warn("DROP: %s", fm.match)
            return
        self._learn_and_forward(p, event.ofp)

def launch():
    def _on_conn_up(ev):
        log.info("Switch conectado: %s", ev.connection)
        L2LearningFirewall(ev.connection)
    core.openflow.addListenerByName("ConnectionUp", _on_conn_up)
    log.info("POX Firewall listo.")
