# T3: Implementación de SDN con Mininet, NFV y Controlador POX

**Autores:** Patrick Peralta, Franklin Pelaez, Miguel Trejo  
**Curso/Práctica:** T3 — SDN + NFV + POX (Firewall)  


## Objetivo
Desarrollar una red definida por software (SDN) controlada por un **controlador POX** personalizado que actúa como **firewall** para bloquear flujos específicos. Además, montar una **NFV** (Network Function Virtualization) que **monitorea HTTP** y registra las solicitudes que hacen los clientes hacia el servidor web.

---

## Estructura del repo
```
t3-sdn/
├─ controller/
│  └─ pox_firewall.py      # Controlador POX con reglas de firewall
├─ topo/
│  └─ custom_topo.py       # Topología Mininet + mirror de tráfico hacia NFV
├─ nfv/
│  └─ http_monitor.py      # NFV con Scapy que registra solicitudes HTTP
└─ requirements.txt        # Dependencia Python para la NFV (scapy)
```

---

## Requisitos
- Ubuntu 20.04+ (o 22.04) con permisos sudo
- **Mininet** y **Open vSwitch**
- **Python 3** y **pip3**
- **POX** (clonado aparte)

Instalación:
```bash
sudo apt-get update
sudo apt-get -y install git python3 python3-pip mininet openvswitch-switch tcpdump
sudo systemctl enable --now openvswitch-switch

# Clonar este repo (ajusta la URL a tu GitHub si corresponde)
git clone <URL_DE_TU_REPO> ~/t3-sdn
cd ~/t3-sdn

# Dependencias Python de la NFV
sudo -H pip3 install -r requirements.txt

# Clonar POX (fuera o al lado del proyecto)
cd ~
git clone https://github.com/noxrepo/pox.git
```

---

## Qué hace cada componente

- **Topología (custom_topo.py):**
  - Hosts: `h1 (10.0.0.1)`, `h2 (10.0.0.2)`, `web1 (10.0.0.3)`, `nfv1 (10.0.0.254)`
  - Un switch `s1` (OVS).
  - Se levanta un **servidor HTTP** en `web1:80`.
  - Se crea un **mirror** (SPAN) en OVS: el tráfico **con destino a `web1`** se **copia** hacia `nfv1` para que la NFV lo analice.

- **Controlador POX (pox_firewall.py):**
  - Conmutador **L2 learning** + **firewall** por reglas.
  - Reglas por defecto:
    - Bloquear **TCP/80** de **h1 → web1** (HTTP).
    - Bloquear **ICMP** desde **h2** a cualquier destino.

- **NFV (http_monitor.py):**
  - Escucha paquetes **HTTP (TCP/80)**.
  - Extrae **método, host y path**, y guarda un log simple en `/tmp/nfv_http.log`.

---

## Cómo ejecutar

### 1) Arrancar el controlador POX (Terminal 1)
```bash
~/pox/pox.py log.level --DEBUG openflow.discovery openflow.spanning_tree misc.full_payload   ~/t3-sdn/controller/pox_firewall.py
```
Deja esa ventana abierta; allí se verán los `DROP` y eventos del switch.

### 2) Levantar la topología (Terminal 2)
```bash
sudo python3 ~/t3-sdn/topo/custom_topo.py
```
Se abrirá la CLI de Mininet (`mininet>`). La topología ya tiene el servidor web levantado y el mirror configurado.

### 3) Iniciar la NFV (dentro de la CLI de Mininet)
```bash
mininet> nfv1 python3 ~/t3-sdn/nfv/http_monitor.py &
```
Debería imprimir algo tipo: `[NFV] HTTP monitor activo. Log: /tmp/nfv_http.log`.

---

## Pruebas rápidas (funcional)

1. **Conectividad básica**
   ```bash
   mininet> pingall
   ```
   Puede fallar ICMP desde `h2` si la regla lo bloquea (es esperado).

2. **HTTP bloqueado (h1 → web1:80)**
   ```bash
   mininet> h1 curl -I http://10.0.0.3
   ```
   Debe **fallar o quedarse colgado** (el firewall hace DROP).  
   En la consola de POX verás una línea `DROP: ...` con el match del flujo.

3. **HTTP permitido (h2 → web1:80)**
   ```bash
   mininet> h2 curl -I http://10.0.0.3
   ```
   Debe responder `HTTP/1.0 200 OK` (o similar).  
   La **NFV** en `nfv1` debe **registrar** la petición:
   ```bash
   mininet> nfv1 tail -n 20 /tmp/nfv_http.log
   ```
   Ejemplo de línea:
   ```
   2025-11-09 20:15:31 10.0.0.2->10.0.0.3 GET http://10.0.0.3/
   ```

4. **Salir**
   ```bash
   mininet> exit
   ```
   Y luego corta POX en la otra terminal con `Ctrl+C` si quieres.

---

## Cómo cambiar las reglas del firewall
Editar en `controller/pox_firewall.py` la lista `FIREWALL_RULES`.  
Ejemplos:

- Bloquear **todo HTTP a web1**, venga de quien venga:
  ```python
  {"nw_proto": 6, "tp_dst": 80, "nw_dst": "10.0.0.3"}
  ```
- Bloquear **ICMP** solo entre `h1` y `h2`:
  ```python
  {"nw_proto": 1, "nw_src": "10.0.0.1", "nw_dst": "10.0.0.2"}
  ```
Después de editar, **reinicia POX**.


---

## Notas finales
- Todo es local y controlado por Mininet + OVS.
