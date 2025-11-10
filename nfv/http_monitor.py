from scapy.all import sniff, TCP, Raw, IP
import re, time

LOG = "/tmp/nfv_http.log"

def parse_http(b):
    t = b.decode('utf-8', errors='ignore')
    m1 = re.match(r'^(GET|POST|HEAD|PUT|DELETE|OPTIONS|PATCH)\s+(\S+)\s+HTTP/\d\.\d', t)
    host = re.search(r'(?im)^\s*Host:\s*([^\r\n]+)', t)
    if m1:
        return m1.group(1), (host.group(1).strip() if host else None), m1.group(2)
    return None

def cb(pkt):
    if pkt.haslayer(TCP) and pkt.haslayer(Raw) and pkt.haslayer(IP) and pkt[TCP].dport == 80:
        p = parse_http(bytes(pkt[Raw]))
        if p:
            method, host, path = p
            line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {pkt[IP].src}->{pkt[IP].dst} {method} http://{host}{path}"
            print(line, flush=True)
            open(LOG, "a").write(line + "\n")

if __name__ == "__main__":
    print(f"[NFV] HTTP monitor activo. Log: {LOG}")
    sniff(filter="tcp port 80", prn=cb, store=False)
