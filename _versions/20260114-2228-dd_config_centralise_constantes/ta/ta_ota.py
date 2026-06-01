"""
project : DTD
Component : TA
file: ta_ota.py

author: jom52
email: jom52.dev@gmail.com
github: https://github.com/JOM52/esp32-dtd

v1.0.0 : 13.01.2026
"""

__version__ = "1.2.2"

import network
import socket
import json
import os
import machine
import time
from machine import UART, Pin

class TAOTAMode:
    def __init__(self):
        self.ap = None
        self.uart = None
        self.dd_online = [False] * 8
        self.dd_ips = [""] * 8  # IP de chaque DD

        self.ssid = "TA_OTA"
        self.password = "12345678"
        self.ip = "192.168.4.1"

        self.uart_index = 2
        self.uart_tx = 43
        self.uart_rx = 44
        self.uart_baud = 9600

        self.udp_sock = None  # Socket UDP pour écouter annonces DD
        self.ota_started = False  # Flag pour savoir si OTA:START a été fait

        # Bouton UP pour retour mode normal
        self.btn_up = None
        self.btn_up_pressed_time = 0
        self.btn_up_last_state = 1
        self.ota_exit_press_ms = 100  # 3s pour sortir du mode OTA

        # Écran TFT
        self.tft = None

    def display_ota_screen(self):
        """Affiche 'Mode OTA' sur l'écran TFT"""
        try:
            import tft_config_amoled as tft_config
            import fonts.vga2_bold_16x32 as font_large
            import fonts.vga2_16x16 as font_small
            import gc

            print("[OTA] Initialisation écran TFT...")

            # Forcer garbage collection pour libérer l'ancienne instance
            gc.collect()

            # Réinitialiser complètement l'écran
            self.tft = tft_config.config(rotation=1)  # Mode paysage

            # Petit délai pour stabilisation
            time.sleep_ms(100)

            # Couleurs
            BLACK = tft_config.color565(0, 0, 0)
            CYAN = tft_config.color565(0, 255, 255)
            YELLOW = tft_config.color565(255, 255, 0)

            # Effacer complètement l'écran
            print("[OTA] Effacement écran...")
            self.tft.fill(BLACK)
            time.sleep_ms(50)

            # Afficher "Mode OTA"
            print("[OTA] Affichage texte...")
            text = "Mode OTA"
            self.tft.text(font_large, text, 60, 30, CYAN, BLACK)

            # Afficher message d'attente
            msg = "Demarrage..."
            self.tft.text(font_small, msg, 50, 75, YELLOW, BLACK)

            print("[OTA] Écran initialisé avec succès")

        except Exception as e:
            print("[OTA] Erreur affichage TFT: {}".format(e))
            import sys
            sys.print_exception(e)
            self.tft = None

    def update_ota_screen_with_ip(self):
        """Met à jour l'écran avec l'adresse IP du serveur"""
        if not self.tft:
            print("[OTA] Écran TFT non disponible, impossible de mettre à jour l'IP")
            return

        try:
            import tft_config_amoled as tft_config
            import fonts.vga2_16x16 as font_small

            print("[OTA] Mise à jour écran avec IP {}...".format(self.ip))

            # Couleurs
            BLACK = tft_config.color565(0, 0, 0)
            GREEN = tft_config.color565(0, 0, 255)
            WHITE = tft_config.color565(255, 255, 255)

            # Effacer la zone du message "Demarrage..."
            self.tft.fill_rect(0, 70, 320, 80, BLACK)
            time.sleep_ms(50)

            # Afficher le SSID (court)
            ssid_text = "SSID: TA_OTA"
            self.tft.text(font_small, ssid_text, 30, 75, WHITE, BLACK)

            # Afficher l'adresse IP (plus court)
            ip_text = self.ip
            self.tft.text(font_small, ip_text, 30, 100, GREEN, BLACK)

            # Message d'information
            info_text = "Port 80"
            self.tft.text(font_small, info_text, 30, 125, WHITE, BLACK)

            print("[OTA] Écran mis à jour avec IP avec succès")

        except Exception as e:
            print("[OTA] Erreur update TFT: {}".format(e))
            import sys
            sys.print_exception(e)

    def setup_uart(self):
        print("[OTA] Init UART{} (TX={}, RX={}, {})".format(
            self.uart_index, self.uart_tx, self.uart_rx, self.uart_baud))

        self.uart = UART(self.uart_index,
                        baudrate=self.uart_baud,
                        tx=Pin(self.uart_tx),
                        rx=Pin(self.uart_rx),
                        timeout=100)

        try:
            pin_set = Pin(45, Pin.OUT)
            pin_set.value(1)
            print("[OTA] Pin SET=1")
        except:
            pass

    def setup_button(self):
        """Initialise le bouton UP pour retour en mode normal"""
        try:
            self.btn_up = Pin(0, Pin.IN, Pin.PULL_UP)
            print("[OTA] Bouton UP (GPIO 0) configuré - Appui long 3s = retour mode normal")
        except Exception as e:
            print("[OTA] Erreur config bouton: {}".format(e))

    def check_exit_button(self):
        """
        Vérifie si le bouton UP est pressé pour sortir du mode OTA
        Retourne True si sortie demandée
        """
        if not self.btn_up:
            return False

        try:
            current_time = time.ticks_ms()
            btn_pressed = (self.btn_up.value() == 0)

            if btn_pressed and self.btn_up_last_state == 1:
                # Début de pression
                self.btn_up_pressed_time = current_time
                self.btn_up_last_state = 0
                print("[OTA] Bouton UP appuyé...")

            elif not btn_pressed and self.btn_up_last_state == 0:
                # Fin de pression
                press_duration = time.ticks_diff(current_time, self.btn_up_pressed_time)
                self.btn_up_last_state = 1

                if press_duration >= self.ota_exit_press_ms:
                    print("[OTA] Bouton UP long ({}ms) → RETOUR MODE NORMAL".format(press_duration))
                    return True

        except Exception as e:
            print("[OTA] Erreur check button: {}".format(e))

        return False
    
    def start_udp_listener(self):
        """Écoute annonces UDP des DD en background"""
        try:
            self.udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_sock.bind(('', 8888))
            self.udp_sock.settimeout(0.1)  # Non-bloquant
            print("[OTA] UDP listener :8888")
        except Exception as e:
            print("[OTA] UDP err: {}".format(e))
    
    def check_udp_announcements(self):
        """Vérifie si des DD s'annoncent"""
        if not self.udp_sock:
            return
        
        try:
            data, addr = self.udp_sock.recvfrom(1024)
            try:
                msg = json.loads(data.decode())
                if msg.get('cmd') == 'hello':
                    dd_id = msg.get('id')
                    dd_ip = msg.get('ip')
                    if dd_id is not None and 0 <= dd_id < 8:
                        if not self.dd_online[dd_id] or self.dd_ips[dd_id] != dd_ip:
                            print("[OTA] DD{:02d} discovered at {} (UDP)".format(dd_id, dd_ip))
                        self.dd_online[dd_id] = True
                        self.dd_ips[dd_id] = dd_ip
            except Exception as e:
                print("[OTA] UDP parse err: {}".format(e))
        except OSError:
            pass  # Timeout normal
    
    def request_dd_announce(self):
        """Demande à tous les DD online de s'annoncer via UDP immédiatement"""
        if not self.udp_sock:
            return
        
        print("[OTA] Requesting DD announcements via UDP broadcast...")
        try:
            # Envoyer commande UDP broadcast pour demander aux DD de s'annoncer
            cmd = json.dumps({"cmd": "announce_request"})
            # Broadcast sur le réseau 192.168.4.255
            self.udp_sock.sendto(cmd.encode(), ('192.168.4.255', 8888))
            print("[OTA] Announce request sent")
        except Exception as e:
            print("[OTA] Announce request err: {}".format(e))
    
    def broadcast_ota_start(self):
        print("[OTA] Broadcast OTA:START...")
        
        for retry in range(3):
            self.uart.write("OTA:START\n")
            time.sleep_ms(500)
            
            buffer = b""
            t0 = time.ticks_ms()
            
            while time.ticks_diff(time.ticks_ms(), t0) < 2500:
                if self.uart.any():
                    buffer += self.uart.read(self.uart.any())
                time.sleep_ms(10)
            
            if buffer:
                try:
                    lines = buffer.decode().split('\n')
                except:
                    lines = []
                
                for line in lines:
                    line = line.strip()
                    if line.startswith("OTA:ACK:"):
                        try:
                            dd_id = int(line[8:10])
                            if 0 <= dd_id < 8:
                                self.dd_online[dd_id] = True
                                print("[OTA] DD{:02d} OK (UART)".format(dd_id))
                        except:
                            pass
            
            if any(self.dd_online):
                break
        
        online_count = sum(self.dd_online)
        print("[OTA] {} DD online: {}".format(
            online_count,
            [i for i in range(8) if self.dd_online[i]]))
        
        # Marquer que OTA:START a été fait
        self.ota_started = True
        
        # Demander aux DD de s'annoncer immédiatement
        time.sleep_ms(500)  # Laisser les DD démarrer leur serveur
        self.request_dd_announce()
        
        # Afficher l'état des IPs
        time.sleep_ms(1000)  # Attendre les annonces
        print("[OTA] IPs: {}".format(
            {i: self.dd_ips[i] for i in range(8) if self.dd_online[i]}))
    
    def setup_wifi_ap(self):
        print("[OTA] AP '{}'...".format(self.ssid))
        
        self.ap = network.WLAN(network.AP_IF)
        self.ap.active(True)
        self.ap.config(essid=self.ssid, 
                      password=self.password,
                      authmode=network.AUTH_WPA2_PSK)
        self.ap.ifconfig((self.ip, '255.255.255.0', self.ip, self.ip))
        
        time.sleep(1)
        
        if self.ap.active():
            print("[OTA] AP: {} (pwd: {})".format(self.ap.ifconfig()[0], self.password))
            return True
        print("[OTA] AP fail")
        return False
    
    def serve_web(self):
        print("[OTA] Web: http://{}".format(self.ip))

        addr = socket.getaddrinfo('0.0.0.0', 80)[0][-1]
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(1)
        sock.settimeout(1.0)  # 1s timeout pour check UDP

        print("[OTA] Listening...")
        print("[OTA] Appui long (3s) sur bouton UP pour retour mode normal")

        try:
            while True:
                # Check bouton UP pour sortie
                if self.check_exit_button():
                    print("[OTA] Sortie mode OTA - Reboot en mode normal...")
                    time.sleep(1)
                    machine.reset()
                    return

                # Check annonces UDP
                self.check_udp_announcements()

                try:
                    cl, addr = sock.accept()
                    print("[OTA] Client: {}".format(addr[0]))
                    self.handle_client(cl)
                    cl.close()
                except OSError:
                    pass  # Timeout normal
        except KeyboardInterrupt:
            print("\n[OTA] Stop")
        finally:
            sock.close()
            if self.udp_sock:
                self.udp_sock.close()
    
    def handle_client(self, client):
        try:
            # Lire headers d'abord
            request = b""
            while b"\r\n\r\n" not in request:
                chunk = client.recv(1024)
                if not chunk:
                    return
                request += chunk
                if len(request) > 100000:  # Sécurité
                    return
            
            # Trouver fin headers
            headers_end = request.find(b"\r\n\r\n")
            headers = request[:headers_end].decode()
            body_start = headers_end + 4
            body = request[body_start:]
            
            # Parser Content-Length
            content_length = 0
            for line in headers.split('\r\n'):
                if line.startswith('Content-Length:'):
                    try:
                        content_length = int(line.split(':', 1)[1].strip())
                    except:
                        pass
            
            # Lire reste du body si nécessaire
            if content_length > 0:
                while len(body) < content_length:
                    chunk = client.recv(min(8192, content_length - len(body)))
                    if not chunk:
                        break
                    body += chunk
            
            # Reconstruire request_str
            request_str = headers + "\r\n\r\n" + body.decode()
            
        except Exception as e:
            print("[OTA] Read err: {}".format(e))
            return
        
        try:
            
            lines = request_str.split('\r\n')
            if not lines:
                return
            
            parts = lines[0].split()
            if len(parts) < 2:
                return
            
            method, path = parts[0], parts[1]
            
            if method == 'GET' and path == '/':
                self.serve_index(client)
            elif method == 'GET' and path == '/status':
                self.serve_status(client)
            elif method == 'POST' and path.startswith('/upload/'):
                self.handle_upload(client, request_str, path)
            elif method == 'POST' and path == '/broadcast_ota':
                self.broadcast_ota_start()
                self.send_json(client, {"status": "ok", "dd_online": self.dd_online, "ota_started": self.ota_started})
            elif method == 'POST' and path == '/refresh':
                # Fonction Refresh pour re-scanner les DD et forcer annonces
                self.broadcast_ota_start()
                self.send_json(client, {"status": "ok", "dd_online": self.dd_online, "dd_ips": self.dd_ips, "ota_started": self.ota_started})
            elif method == 'POST' and path == '/reboot_all_dd':
                self.handle_reboot_all_dd(client)
            else:
                self.send_response(client, 404, "Not Found")
                
        except Exception as e:
            print("[OTA] Err: {}".format(e))
    
    def serve_index(self, client):
        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TA OTA</title>
<style>
body{font-family:monospace;max-width:800px;margin:20px auto;padding:20px;background:#111;color:#0f0}
h1{color:#0ff;border-bottom:2px solid #0ff;padding-bottom:10px}
.section{background:#222;border:1px solid #444;padding:15px;margin:15px 0;border-radius:5px}
.dd-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:10px 0}
.dd-box{padding:10px;text-align:center;border:1px solid #444;border-radius:3px;font-size:11px}
.dd-on{background:#050;color:#0f0}
.dd-waiting{background:#330;color:#ff0}
.dd-off{background:#300;color:#f00}
button{background:#044;color:#0ff;border:1px solid #0ff;padding:10px 20px;cursor:pointer;margin:5px;font-family:monospace}
button:hover{background:#066}
button:disabled{background:#222;color:#666;cursor:not-allowed;border-color:#444}
input[type="file"]{color:#0f0;margin:0 10px 0 0;font-size:12px}
input[type="file"]:disabled{color:#666}
select{background:#222;color:#0f0;border:1px solid #444;padding:5px;font-family:monospace;margin:0 10px}
select:disabled{color:#666;border-color:#444}
#log{background:#000;color:#0f0;padding:10px;height:150px;overflow-y:auto;font-size:12px;border:1px solid #444}
.upload-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.warning{color:#ff0;font-size:12px;margin-top:5px}
</style>
</head>
<body>
<h1>TA OTA v1.2.2</h1>
<div class="section">
<h3>DD Status</h3>
<div class="dd-grid" id="ddStatus"></div>
<button onclick="broadcastOTA()" id="btnOtaStart">OTA:START</button>
<button onclick="doRefresh()">Refresh</button>
<button onclick="rebootAllDD()" style="background:#600;border-color:#f00">Reboot All DD</button>
<div class="warning" id="warningOta" style="display:none">⚠️ Veuillez d'abord cliquer sur OTA:START</div>
</div>
<div class="section">
<h3>Upload</h3>
<div class="upload-row">
<input type="file" id="fileInput" accept=".py" disabled>
<label>Target: 
<select id="target" disabled>
<option value="ta">TA</option>
<option value="0">DD0</option>
<option value="1">DD1</option>
<option value="2">DD2</option>
<option value="3">DD3</option>
<option value="4">DD4</option>
<option value="5">DD5</option>
<option value="6">DD6</option>
<option value="7">DD7</option>
</select>
</label>
<button onclick="uploadFile()" id="btnFlash" disabled>Flash</button>
</div>
<div class="warning" id="warningFlash">⚠️ Cliquez sur OTA:START pour activer le flashage</div>
</div>
<div class="section">
<h3>Log</h3>
<div id="log"></div>
</div>
<script>
let lastDdStatus = [false,false,false,false,false,false,false,false];
let otaStarted = false;

function log(msg){const l=document.getElementById('log');l.innerHTML+=new Date().toLocaleTimeString()+' - '+msg+'<br>';l.scrollTop=l.scrollHeight}

function updateFlashControls(enabled){
    otaStarted = enabled;
    document.getElementById('fileInput').disabled = !enabled;
    document.getElementById('target').disabled = !enabled;
    document.getElementById('btnFlash').disabled = !enabled;
    document.getElementById('warningFlash').style.display = enabled ? 'none' : 'block';
    document.getElementById('warningOta').style.display = 'none';
}

function refreshStatus(){
    fetch('/status').then(r=>r.json()).then(data=>{
        // Mettre à jour l'état OTA
        if(data.ota_started && !otaStarted){
            updateFlashControls(true);
            log('OTA mode activated - Flash enabled');
        }
        
        const g=document.getElementById('ddStatus');
        g.innerHTML='';
        let changed=false;
        for(let i=0;i<8;i++){
            const b=document.createElement('div');
            let status='';
            let cssClass='';
            
            if(data.dd_online[i]){
                if(data.dd_ips[i] && data.dd_ips[i]!==''){
                    // Online avec IP
                    cssClass='dd-on';
                    status='DD'+i+'\\n'+data.dd_ips[i];
                }else{
                    // Online mais pas d'IP (attend UDP)
                    cssClass='dd-waiting';
                    status='DD'+i+'\\nWAIT IP';
                }
            }else{
                // Offline
                cssClass='dd-off';
                status='DD'+i+'\\nOFF';
            }
            
            b.className='dd-box '+cssClass;
            b.textContent=status;
            g.appendChild(b);
            
            if(data.dd_online[i]!==lastDdStatus[i]){
                changed=true;
                lastDdStatus[i]=data.dd_online[i];
                log('DD'+i+' '+(data.dd_online[i]?'ONLINE':'OFFLINE'));
            }
        }
    }).catch(err=>log('ERR: '+err))
}

function doRefresh(){
    log('Scanning for DD...');
    fetch('/refresh',{method:'POST'}).then(r=>r.json()).then(data=>{
        log('Scan complete');
        if(data.ota_started){
            updateFlashControls(true);
        }
        refreshStatus();
    }).catch(err=>log('ERR: '+err))
}

function broadcastOTA(){
    log('Sending OTA:START...');
    fetch('/broadcast_ota',{method:'POST'}).then(r=>r.json()).then(data=>{
        log('Broadcast sent');
        if(data.ota_started){
            updateFlashControls(true);
        }
        setTimeout(refreshStatus,2000);
    }).catch(err=>log('ERR: '+err))
}

function rebootAllDD(){
    if(!confirm('Reboot all DD to normal mode?'))return;
    log('Rebooting all DD...');
    fetch('/reboot_all_dd',{method:'POST'}).then(r=>r.json()).then(data=>{
        log('Reboot sent to '+data.count+' DD');
        setTimeout(()=>{
            lastDdStatus=[false,false,false,false,false,false,false,false];
            updateFlashControls(false);
            refreshStatus();
        },3000);
    }).catch(err=>log('ERR: '+err))
}

function uploadFile(){
    if(!otaStarted){
        alert('Veuillez d\\'abord cliquer sur OTA:START');
        document.getElementById('warningOta').style.display='block';
        return;
    }
    
    const file=document.getElementById('fileInput').files[0];
    const target=document.getElementById('target').value;
    if(!file){alert('Select file');return}
    
    log('Uploading '+file.name+' ('+file.size+' bytes) to '+target+'...');
    const reader=new FileReader();
    reader.onload=function(e){
        const content=e.target.result;
        fetch('/upload/'+target,{
            method:'POST',
            headers:{
                'X-Filename':file.name,
                'Content-Length':content.length.toString()
            },
            body:content
        }).then(r=>r.json()).then(data=>{
            data.status==='ok'?log('SUCCESS: '+target+' updated'):log('FAILED: '+data.message)
        }).catch(err=>log('ERR: '+err))
    };
    reader.readAsText(file,'UTF-8');
}

log('Interface ready');
refreshStatus();
setInterval(refreshStatus,3000);
</script>
</body>
</html>"""
        
        response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: {}\r\n\r\n{}".format(len(html), html)
        client.send(response.encode())
    
    def serve_status(self, client):
        self.send_json(client, {
            "dd_online": self.dd_online,
            "dd_ips": self.dd_ips,
            "ip": self.ip,
            "version": __version__,
            "ota_started": self.ota_started
        })
    
    def handle_upload(self, client, request_str, path):
        target = path.split('/')[-1]
        
        filename = "main.py"
        for line in request_str.split('\r\n'):
            if line.startswith('X-Filename:'):
                filename = line.split(':', 1)[1].strip()
                break
        
        body_start = request_str.find('\r\n\r\n')
        if body_start == -1:
            self.send_json(client, {"status": "error", "message": "Bad request"})
            return
        
        file_content = request_str[body_start + 4:]
        
        if target == 'ta':
            print("[OTA] Upload {} ({} bytes) -> TA".format(filename, len(file_content)))
            
            try:
                if filename in os.listdir('/'):
                    os.rename(filename, filename + ".bak")
                
                with open(filename, 'w') as f:
                    f.write(file_content)
                
                print("[OTA] {} written".format(filename))
                
                self.send_json(client, {
                    "status": "ok",
                    "message": "TA updated. Reboot in 3s",
                    "filename": filename
                })
                
                print("[OTA] Reboot in 3s...")
                time.sleep(3)
                machine.reset()
                
            except Exception as e:
                self.send_json(client, {"status": "error", "message": str(e)})
        
        else:
            # Upload vers DD
            try:
                dd_id = int(target)
                if not (0 <= dd_id < 8):
                    raise ValueError("DD ID invalid")
                
                if not self.dd_online[dd_id]:
                    self.send_json(client, {"status": "error", "message": "DD{:02d} offline".format(dd_id)})
                    return
                
                dd_ip = self.dd_ips[dd_id]
                if not dd_ip:
                    self.send_json(client, {"status": "error", "message": "DD{:02d} IP unknown (wait for UDP announce or click Refresh)".format(dd_id)})
                    return
                
                print("[OTA] Upload {} -> DD{:02d} ({})".format(filename, dd_id, dd_ip))
                
                # Envoyer fichier au DD via HTTP
                result = self.upload_to_dd(dd_ip, filename, file_content)
                
                if result:
                    self.send_json(client, {
                        "status": "ok",
                        "message": "DD{:02d} updated successfully".format(dd_id),
                        "dd_id": dd_id
                    })
                else:
                    self.send_json(client, {
                        "status": "error",
                        "message": "DD{:02d} upload failed".format(dd_id)
                    })
                
            except Exception as e:
                self.send_json(client, {"status": "error", "message": str(e)})
    
    def upload_to_dd(self, dd_ip, filename, content):
        """Envoie fichier au DD via HTTP POST"""
        try:
            print("[OTA] Connecting to DD at {}:8080...".format(dd_ip))
            
            # Créer requête HTTP
            request = "POST /ota/update HTTP/1.1\r\n"
            request += "Host: {}\r\n".format(dd_ip)
            request += "X-Filename: {}\r\n".format(filename)
            request += "Content-Length: {}\r\n".format(len(content))
            request += "\r\n"
            request += content
            
            print("[OTA] Sending {} bytes...".format(len(request)))
            
            # Connexion au DD
            addr = socket.getaddrinfo(dd_ip, 8080)[0][-1]
            sock = socket.socket()
            sock.settimeout(60.0)
            
            try:
                sock.connect(addr)
            except OSError as e:
                err_num = e.args[0] if e.args else 0
                if err_num == 113:  # ECONNABORTED
                    print("[OTA] Connection refused (DD may have rebooted)")
                elif err_num == 111:  # ECONNREFUSED
                    print("[OTA] DD not listening")
                else:
                    print("[OTA] Connect err: {} [{}]".format(e, err_num))
                return False
            
            # Envoyer en chunks pour gros fichiers
            chunk_size = 1024
            sent = 0
            request_bytes = request.encode()
            
            while sent < len(request_bytes):
                chunk = request_bytes[sent:sent + chunk_size]
                try:
                    n = sock.send(chunk)
                    sent += n
                except OSError as e:
                    err_num = e.args[0] if e.args else 0
                    if err_num == 113:
                        print("[OTA] Connection aborted during send")
                        sock.close()
                        return False
                    raise
                
                if sent % 5120 == 0:
                    print("[OTA] Sent {}/{}...".format(sent, len(request_bytes)))
            
            print("[OTA] Upload complete, waiting response...")
            
            # Lire réponse complète - IMPORTANT: DD peut mettre 10-15s à écrire gros fichier
            response = b""
            sock.settimeout(20.0)  # 20s au lieu de 10s
            start = time.ticks_ms()
            
            print("[OTA] Waiting up to 20s for response...")
            
            while time.ticks_diff(time.ticks_ms(), start) < 20000:
                try:
                    chunk = sock.recv(1024)
                    if not chunk:
                        # Attendre un peu plus au cas où
                        time.sleep_ms(100)
                        chunk = sock.recv(1024)
                        if not chunk:
                            print("[OTA] No more data")
                            break
                    
                    response += chunk
                    print("[OTA] Recv: {} bytes, total: {}".format(len(chunk), len(response)))
                    
                    # Si on a headers complets + body JSON, on peut arrêter
                    if b"\r\n\r\n" in response and b"}" in response:
                        print("[OTA] Complete response")
                        break
                        
                except Exception as e:
                    err_num = e.args[0] if e.args else 0
                    err_str = str(e)
                    
                    if err_num == 113 or 'ECONNABORTED' in err_str:
                        print("[OTA] Connection aborted during recv")
                        break
                    elif 'timeout' not in err_str.lower():
                        print("[OTA] Recv err: {}".format(e))
                        break
                    time.sleep_ms(100)
            
            sock.close()
            
            print("[OTA] Response: {} bytes".format(len(response)))
            if len(response) > 0:
                print("[OTA] Response: {}".format(response[:300]))
            
            success = b"200 OK" in response or b'"status":"ok"' in response or b'"status": "ok"' in response
            
            if success:
                print("[OTA] Upload SUCCESS")
            else:
                print("[OTA] Upload FAILED (no success marker)")
            
            return success
            
        except OSError as e:
            err_num = e.args[0] if e.args else 0
            if err_num == 113:
                print("[OTA] Connection aborted (DD offline/rebooted)")
            else:
                print("[OTA] Upload err: {} [errno {}]".format(e, err_num))
            return False
            
        except Exception as e:
            print("[OTA] Upload err: {}".format(e))
            return False
    
    def handle_reboot_all_dd(self, client):
        """Envoie commande reboot à tous les DD en mode OTA"""
        print("[OTA] Rebooting all DD...")
        count = 0
        
        for dd_id in range(8):
            if self.dd_online[dd_id] and self.dd_ips[dd_id]:
                dd_ip = self.dd_ips[dd_id]
                print("[OTA] Reboot DD{:02d} ({})...".format(dd_id, dd_ip))
                
                try:
                    # Envoyer GET /reboot au DD
                    addr = socket.getaddrinfo(dd_ip, 8080)[0][-1]
                    sock = socket.socket()
                    sock.settimeout(2.0)
                    sock.connect(addr)
                    sock.send(b"GET /reboot HTTP/1.1\r\n\r\n")
                    sock.close()
                    count += 1
                    print("[OTA] DD{:02d} reboot sent".format(dd_id))
                except Exception as e:
                    print("[OTA] DD{:02d} reboot err: {}".format(dd_id, e))
        
        print("[OTA] {} DD reboot commands sent".format(count))
        self.send_json(client, {"status": "ok", "count": count})
    
    def send_response(self, client, code, message):
        status = {200: "OK", 404: "Not Found", 500: "Error"}
        response = "HTTP/1.1 {} {}\r\nContent-Type: text/plain\r\n\r\n{}".format(code, status.get(code, '?'), message)
        client.send(response.encode())
    
    def send_json(self, client, data):
        json_str = json.dumps(data)
        response = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}".format(len(json_str), json_str)
        client.send(response.encode())


def enter_ota_mode():
    print("\n{}".format("="*50))
    print("  MODE OTA TA v{}".format(__version__))
    print("{}".format("="*50))

    ota = TAOTAMode()

    # Afficher "Mode OTA" sur l'écran TFT
    ota.display_ota_screen()

    ota.setup_uart()
    ota.setup_button()  # Configurer le bouton UP

    if not ota.setup_wifi_ap():
        print("[OTA] WiFi fail. Reboot...")
        time.sleep(3)
        machine.reset()
        return

    ota.start_udp_listener()

    # Mettre à jour l'écran avec l'adresse IP
    ota.update_ota_screen_with_ip()

    try:
        ota.serve_web()
    except KeyboardInterrupt:
        print("\n[OTA] Stop")
    finally:
        if ota.ap:
            ota.ap.active(False)