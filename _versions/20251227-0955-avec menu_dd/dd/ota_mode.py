"""
ota_mode.py v1.2.2 - Mode OTA pour DD
Support commande UDP pour annonce à la demande

v1.2.2:
- Réponse à la commande UDP "announce_request" pour annonce immédiate
- Amélioration de la découverte par le TA
v1.2.1:
- Annonces UDP périodiques toutes les 30s
v1.2.0:
- Extraction du filename depuis Content-Disposition header
- Support header personnalisé X-Filename
"""

__version__ = "1.2.2"

import network
import socket
import json
import os
import machine
import time
import gc

try:
    import utils.nvs_utils as nvs_utils
except ImportError:
    nvs_utils = None

class OTAMode:
    def __init__(self, dd_id):
        self.dd_id = dd_id
        self.wlan = None
        self.connected = False
        self.ta_ssid = "TA_OTA"
        self.ta_password = "12345678"
        self.ta_ip = "192.168.4.1"
        self.ota_port = 8080
        
        # Socket UDP pour écouter les commandes du TA
        self.udp_listen_sock = None
        
    def enable_wifi(self):
        print("[OTA] DD{:02d} - WiFi...".format(self.dd_id))
        
        # CRITIQUE: Libérer mémoire AVANT d'activer WiFi
        gc.collect()
        
        # Désactiver AP si actif (libère mémoire)
        try:
            ap = network.WLAN(network.AP_IF)
            if ap.active():
                print("[OTA] Désactivation AP...")
                ap.active(False)
                time.sleep_ms(100)
                gc.collect()
        except:
            pass
        
        # Activer STA avec précautions
        try:
            self.wlan = network.WLAN(network.STA_IF)
            
            # Si déjà actif, le désactiver d'abord
            if self.wlan.active():
                print("[OTA] Reset WiFi...")
                self.wlan.active(False)
                time.sleep_ms(200)
                gc.collect()
            
            # Activer maintenant
            self.wlan.active(True)
            time.sleep_ms(500)
            
        except Exception as e:
            print("[OTA] ERREUR activation WiFi:", e)
            return False
        
        print("[OTA] Connexion {}...".format(self.ta_ssid))
        
        try:
            self.wlan.connect(self.ta_ssid, self.ta_password)
        except Exception as e:
            print("[OTA] ERREUR connect:", e)
            return False
        
        for _ in range(10):
            if self.wlan.isconnected():
                self.connected = True
                print("[OTA] OK! IP: {}".format(self.wlan.ifconfig()[0]))
                return True
            time.sleep(1)
        
        print("[OTA] Échec WiFi")
        return False
    
    def announce_to_ta(self):
        if not self.connected:
            return False
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = json.dumps({"cmd": "hello", "id": self.dd_id, "ip": self.wlan.ifconfig()[0]})
            sock.sendto(msg.encode(), (self.ta_ip, 8888))
            sock.close()
            print("[OTA] Annonce")
            return True
        except:
            return False
    
    def setup_udp_listener(self):
        """Configure un listener UDP pour recevoir les commandes du TA"""
        try:
            self.udp_listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.udp_listen_sock.bind(('', 8888))
            self.udp_listen_sock.settimeout(0.1)  # Non-bloquant
            print("[OTA] UDP command listener :8888")
        except Exception as e:
            print("[OTA] UDP listener err: {}".format(e))
    
    def check_udp_commands(self):
        """Vérifie si le TA envoie des commandes UDP"""
        if not self.udp_listen_sock:
            return
        
        try:
            data, addr = self.udp_listen_sock.recvfrom(1024)
            try:
                msg = json.loads(data.decode())
                cmd = msg.get('cmd')
                
                if cmd == 'announce_request':
                    print("[OTA] Announce requested by TA")
                    # Envoyer immédiatement l'annonce
                    self.announce_to_ta()
                    
            except:
                pass
        except OSError:
            pass  # Timeout normal
    
    def start_ota_server(self):
        if not self.connected:
            return
        
        print("[OTA] Server :{}...".format(self.ota_port))
        addr = socket.getaddrinfo('0.0.0.0', self.ota_port)[0][-1]
        sock = socket.socket()
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        sock.listen(1)
        sock.settimeout(30.0)  # 30s timeout pour annonces périodiques
        
        print("[OTA] Ready")
        
        # Compteur pour annonces périodiques
        announce_counter = 0
        
        try:
            while True:
                # Vérifier les commandes UDP du TA
                self.check_udp_commands()
                
                try:
                    cl, addr = sock.accept()
                    cl.settimeout(60.0)
                    print("[OTA] Client {}".format(addr[0]))
                    self.handle_request(cl)
                    cl.close()
                except OSError as e:
                    if 'timeout' in str(e).lower():
                        # Envoyer annonce UDP périodiquement
                        announce_counter += 1
                        print("[OTA] Keepalive #{} - Sending UDP announce...".format(announce_counter))
                        self.announce_to_ta()
                        continue
                    break
        except KeyboardInterrupt:
            print("[OTA] Stop")
        finally:
            sock.close()
            if self.udp_listen_sock:
                self.udp_listen_sock.close()
    
    def extract_filename_from_headers(self, lines):
        """
        Extrait le nom de fichier depuis les headers HTTP.
        Supporte:
        1. Content-Disposition: attachment; filename="dd_main.py"
        2. Content-Disposition: form-data; name="file"; filename="dd_main.py"
        3. X-Filename: dd_main.py (header personnalisé)
        """
        filename = None
        
        for line in lines:
            lower_line = line.lower()
            
            # Méthode 1: Header X-Filename (le plus simple)
            if lower_line.startswith('x-filename:'):
                filename = line.split(':', 1)[1].strip()
                print("[OTA] Filename extrait de X-Filename: {}".format(filename))
                return filename
            
            # Méthode 2: Content-Disposition
            elif lower_line.startswith('content-disposition:'):
                # Chercher filename="..."
                if 'filename=' in lower_line:
                    # Trouver la position de filename=
                    idx = line.lower().find('filename=')
                    if idx != -1:
                        # Extraire après filename=
                        filename_part = line[idx + 9:].strip()
                        
                        # Vérifier si entre guillemets
                        if filename_part.startswith('"'):
                            # Chercher le guillemet fermant
                            end_idx = filename_part.find('"', 1)
                            if end_idx != -1:
                                filename = filename_part[1:end_idx]
                        else:
                            # Pas de guillemets, prendre jusqu'au prochain ; ou fin de ligne
                            end_idx = filename_part.find(';')
                            if end_idx != -1:
                                filename = filename_part[:end_idx].strip()
                            else:
                                filename = filename_part.strip()
                        
                        if filename:
                            print("[OTA] Filename extrait de Content-Disposition: {}".format(filename))
                            return filename
        
        return None
    
    def handle_request(self, client):
        try:
            request = client.recv(8192)
            if not request:
                return
                
            try:
                request_str = request.decode()
            except:
                print("[OTA] Decode error")
                return
            
            lines = request_str.split('\r\n')
            if not lines:
                return
            
            first_line = lines[0]
            parts = first_line.split()
            if len(parts) < 2:
                return
            
            method = parts[0]
            path = parts[1]
            
            print("[OTA] {} {}".format(method, path))
            
            if method == "GET":
                if path == "/":
                    self.send_index_page(client)
                elif path == "/status":
                    self.send_status(client)
                elif path.startswith("/file/"):
                    filename = path[6:]
                    self.send_file(client, filename)
                elif path == "/list":
                    self.send_file_list(client)
                elif path == "/reboot":
                    self.handle_reboot(client)
                else:
                    self.send_404(client)
            
            elif method == "POST":
                # Parser Content-Length et Content-Type
                content_length = 0
                content_type = ""
                for line in lines:
                    lower_line = line.lower()
                    if lower_line.startswith('content-length:'):
                        content_length = int(line.split(':')[1].strip())
                    elif lower_line.startswith('content-type:'):
                        content_type = line.split(':')[1].strip()
                
                if path == "/upload" or path.startswith("/ota/update"):
                    if content_length > 0:
                        body_start = request_str.find('\r\n\r\n')
                        if body_start != -1:
                            body_start += 4
                            body = request[body_start:]
                            
                            remaining = content_length - len(body)
                            while remaining > 0:
                                chunk = client.recv(min(remaining, 4096))
                                if not chunk:
                                    break
                                body += chunk
                                remaining -= len(chunk)
                            
                            # Méthode 1: Extraire le filename depuis les headers HTTP
                            filename = self.extract_filename_from_headers(lines)
                            
                            # Méthode 2: Extraire le filename du path si présent (ex: /ota/update?file=dd_main.py)
                            if not filename and '?' in path:
                                query_start = path.find('?')
                                query = path[query_start+1:]
                                for param in query.split('&'):
                                    if '=' in param:
                                        key, value = param.split('=', 1)
                                        if key == 'file':
                                            filename = value
                                            print("[OTA] Filename extrait du paramètre ?file=: {}".format(filename))
                                            break
                            
                            self.handle_upload(client, body, content_type, filename)
                    else:
                        self.send_400(client)
                
                elif path == "/delete":
                    if content_length > 0:
                        body_start = request_str.find('\r\n\r\n')
                        if body_start != -1:
                            body_start += 4
                            body = request[body_start:].encode() if isinstance(request_str, str) else request[body_start:]
                            
                            remaining = content_length - len(body)
                            while remaining > 0:
                                chunk = client.recv(min(remaining, 4096))
                                if not chunk:
                                    break
                                body += chunk
                                remaining -= len(chunk)
                            
                            self.handle_delete(client, body)
                    else:
                        self.send_400(client)
                else:
                    self.send_404(client)
            else:
                self.send_404(client)
                
        except Exception as e:
            print("[OTA] Request error:", e)
            import sys
            sys.print_exception(e)
    
    def send_response(self, client, status_code, body, content_type="text/plain"):
        try:
            status_text = {
                200: "OK",
                400: "Bad Request",
                404: "Not Found",
                500: "Internal Server Error"
            }.get(status_code, "Unknown")
            
            if isinstance(body, str):
                body = body.encode()
            
            response = "HTTP/1.1 {} {}\r\n".format(status_code, status_text)
            response += "Content-Type: {}\r\n".format(content_type)
            response += "Content-Length: {}\r\n".format(len(body))
            response += "Connection: close\r\n"
            response += "\r\n"
            
            client.send(response.encode())
            client.send(body)
        except:
            pass
    
    def send_404(self, client):
        self.send_response(client, 404, "Not Found")
    
    def send_400(self, client):
        self.send_response(client, 400, "Bad Request")
    
    def send_index_page(self, client):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>OTA DD{:02d}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .container {{
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 600px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }}
        h1 {{
            color: #667eea;
            margin-bottom: 10px;
            font-size: 2em;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
        }}
        .upload-zone {{
            border: 3px dashed #667eea;
            border-radius: 15px;
            padding: 40px;
            text-align: center;
            margin-bottom: 30px;
            background: #f8f9ff;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .upload-zone:hover {{
            background: #eef0ff;
            border-color: #764ba2;
        }}
        .upload-zone.dragover {{
            background: #e0e4ff;
            border-color: #764ba2;
        }}
        input[type="file"] {{
            display: none;
        }}
        button {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
            margin: 5px;
        }}
        button:hover {{
            transform: translateY(-2px);
        }}
        button:active {{
            transform: translateY(0);
        }}
        #fileList {{
            margin-top: 30px;
        }}
        .file-item {{
            background: #f8f9ff;
            padding: 15px;
            margin: 10px 0;
            border-radius: 10px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .file-info {{
            flex: 1;
        }}
        .file-name {{
            font-weight: 600;
            color: #333;
        }}
        .file-size {{
            color: #666;
            font-size: 14px;
        }}
        .file-actions {{
            display: flex;
            gap: 10px;
        }}
        .btn-small {{
            padding: 8px 20px;
            font-size: 14px;
        }}
        .btn-danger {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        }}
        .status {{
            margin: 20px 0;
            padding: 15px;
            border-radius: 10px;
            display: none;
        }}
        .status.success {{
            background: #d4edda;
            color: #155724;
            display: block;
        }}
        .status.error {{
            background: #f8d7da;
            color: #721c24;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>OTA DD{:02d}</h1>
        <p class="subtitle">Mode mise à jour sans fil</p>
        
        <div class="upload-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
            <div style="font-size: 48px; margin-bottom: 10px;">📁</div>
            <div style="font-size: 18px; margin-bottom: 10px;">Glissez un fichier ici</div>
            <div style="color: #666;">ou cliquez pour sélectionner</div>
            <input type="file" id="fileInput" onchange="uploadFile(this.files[0])">
        </div>
        
        <div id="status" class="status"></div>
        
        <div style="text-align: center;">
            <button onclick="loadFileList()">🔄 Actualiser</button>
            <button onclick="reboot()">🔌 Redémarrer</button>
        </div>
        
        <div id="fileList"></div>
    </div>
    
    <script>
        // Drag & Drop
        const dropZone = document.getElementById('dropZone');
        
        dropZone.addEventListener('dragover', (e) => {{
            e.preventDefault();
            dropZone.classList.add('dragover');
        }});
        
        dropZone.addEventListener('dragleave', () => {{
            dropZone.classList.remove('dragover');
        }});
        
        dropZone.addEventListener('drop', (e) => {{
            e.preventDefault();
            dropZone.classList.remove('dragover');
            if (e.dataTransfer.files.length) {{
                uploadFile(e.dataTransfer.files[0]);
            }}
        }});
        
        function showStatus(message, isError = false) {{
            const status = document.getElementById('status');
            status.textContent = message;
            status.className = 'status ' + (isError ? 'error' : 'success');
            setTimeout(() => {{
                status.style.display = 'none';
            }}, 5000);
        }}
        
        function uploadFile(file) {{
            if (!file) return;
            
            showStatus('Upload en cours: ' + file.name);
            
            // IMPORTANT: Envoyer le nom de fichier dans le header X-Filename
            fetch('/ota/update', {{
                method: 'POST',
                headers: {{
                    'X-Filename': file.name
                }},
                body: file
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'ok') {{
                    showStatus('✓ ' + file.name + ' uploadé (' + data.size + ' bytes)');
                    loadFileList();
                }} else {{
                    showStatus('✗ Erreur: ' + data.message, true);
                }}
            }})
            .catch(err => {{
                showStatus('✗ Erreur: ' + err, true);
            }});
        }}
        
        function loadFileList() {{
            fetch('/list')
            .then(response => response.json())
            .then(data => {{
                const fileList = document.getElementById('fileList');
                if (data.files.length === 0) {{
                    fileList.innerHTML = '<p style="text-align: center; color: #666;">Aucun fichier</p>';
                    return;
                }}
                
                let html = '<h3 style="margin-bottom: 15px;">Fichiers (/) :</h3>';
                data.files.forEach(file => {{
                    html += `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-name">${{file.name}}</div>
                                <div class="file-size">${{file.size}} bytes</div>
                            </div>
                            <div class="file-actions">
                                <button class="btn-small" onclick="downloadFile('${{file.name}}')">⬇️</button>
                                <button class="btn-small btn-danger" onclick="deleteFile('${{file.name}}')">🗑️</button>
                            </div>
                        </div>
                    `;
                }});
                fileList.innerHTML = html;
            }});
        }}
        
        function deleteFile(filename) {{
            if (!confirm('Supprimer ' + filename + ' ?')) return;
            
            fetch('/delete', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ filename: filename }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (data.status === 'ok') {{
                    showStatus('✓ ' + filename + ' supprimé');
                    loadFileList();
                }} else {{
                    showStatus('✗ Erreur: ' + data.message, true);
                }}
            }});
        }}
        
        function downloadFile(filename) {{
            window.location.href = '/file/' + filename;
        }}
        
        function reboot() {{
            if (!confirm('Redémarrer le DD?')) return;
            showStatus('DD en cours de redémarrage...');
            fetch('/reboot', {{ method: 'POST' }});
        }}
        
        loadFileList();
    </script>
</body>
</html>""".format(self.dd_id, self.dd_id)
        
        self.send_response(client, 200, html, "text/html")
    
    def send_status(self, client):
        try:
            import os
            stat = os.statvfs('/')
            free = stat[0] * stat[3]
            total = stat[0] * stat[2]
        except:
            free = 0
            total = 0
        
        status = {
            "dd_id": self.dd_id,
            "version": __version__,
            "free_space": free,
            "total_space": total,
        }
        self.send_response(client, 200, json.dumps(status), "application/json")
    
    def send_file_list(self, client):
        files = []
        try:
            for f in os.listdir('/'):
                try:
                    stat = os.stat('/' + f)
                    files.append({"name": f, "size": stat[6]})
                except:
                    pass
        except:
            pass
        
        self.send_response(client, 200, json.dumps({"files": files}), "application/json")
    
    def send_file(self, client, filename):
        try:
            filepath = '/' + filename
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(client, 200, content, "application/octet-stream")
        except:
            self.send_404(client)
    
    def handle_upload(self, client, body, content_type, filename_hint=None):
        """
        Gère l'upload de fichier en supportant deux formats:
        1. multipart/form-data (avec Content-Disposition)
        2. raw body (le contenu complet du fichier)
        
        Le filename peut venir de:
        1. Header X-Filename (priorité)
        2. Paramètre ?file= dans l'URL
        3. Content-Disposition dans le body multipart
        4. Nom par défaut "uploaded_file.bin"
        """
        try:
            print("[OTA] Upload: {} bytes, type: {}".format(len(body), content_type))
            
            filename = filename_hint  # Nom de fichier fourni dans l'URL ou headers
            file_content = None
            
            # Tenter de parser en multipart/form-data
            if b'Content-Disposition' in body:
                print("[OTA] Format: multipart/form-data")
                
                boundary_start = body.find(b'Content-Disposition')
                if boundary_start != -1:
                    # Si pas de filename dans les headers HTTP, chercher dans le body
                    if not filename:
                        filename_start = body.find(b'filename="', boundary_start)
                        if filename_start != -1:
                            filename_start += 10
                            filename_end = body.find(b'"', filename_start)
                            filename = body[filename_start:filename_end].decode()
                            print("[OTA] Filename extrait du body multipart: {}".format(filename))
                    
                    content_start = body.find(b'\r\n\r\n', boundary_start) + 4
                    boundary_end = body.rfind(b'------')
                    
                    if boundary_end > content_start:
                        file_content = body[content_start:boundary_end-2]
                    else:
                        file_content = body[content_start:]
            
            # Si pas multipart ou parsing échoué, traiter comme raw body
            if file_content is None:
                print("[OTA] Format: raw body")
                file_content = body
                
                # Si pas de filename fourni, utiliser un nom par défaut
                if not filename:
                    filename = "uploaded_file.bin"
                    print("[OTA] Aucun filename fourni, utilisation du nom par défaut")
            
            if not filename:
                print("[OTA] ERROR: No filename")
                self.send_400(client)
                return
            
            print("[OTA] Filename final: {}".format(filename))
            print("[OTA] Content: {} bytes".format(len(file_content)))
            
            # Écrire le fichier
            filepath = '/' + filename
            with open(filepath, 'wb') as f:
                f.write(file_content)
            
            print("[OTA] File saved: {}".format(filepath))
            
            response = json.dumps({"status": "ok", "filename": filename, "size": len(file_content)})
            self.send_response(client, 200, response, "application/json")
            
        except Exception as e:
            print("[OTA] Upload error:", e)
            import sys
            sys.print_exception(e)
            response = json.dumps({"status": "error", "message": str(e)})
            self.send_response(client, 500, response, "application/json")
    
    def handle_delete(self, client, body):
        try:
            data = json.loads(body.decode())
            filename = data.get('filename')
            
            if filename:
                os.remove('/' + filename)
                response = json.dumps({"status": "ok"})
                self.send_response(client, 200, response, "application/json")
            else:
                response = json.dumps({"status": "error", "message": "No filename"})
                self.send_response(client, 400, response, "application/json")
        except Exception as e:
            response = json.dumps({"status": "error", "message": str(e)})
            self.send_response(client, 500, response, "application/json")
    
    def handle_reboot(self, client):
        """Gère la requête de redémarrage (GET ou POST)"""
        try:
            print("[OTA] Reboot demandé")
            response = json.dumps({"status": "ok", "message": "Rebooting..."})
            self.send_response(client, 200, response, "application/json")
            
            # IMPORTANT: Fermer le client proprement
            try:
                client.close()
            except:
                pass
            
            # Attendre que la réponse parte
            time.sleep_ms(200)
            
            # Effacer le flag OTA avant de redémarrer
            if nvs_utils:
                print("[OTA] Effacement flag OTA...")
                nvs_utils.set_i32("DTD", "ota_mode", 0)
            
            # Redémarrer
            print("[OTA] Reboot NOW")
            machine.reset()
            
        except Exception as e:
            print("[OTA] Erreur reboot:", e)
            try:
                response = json.dumps({"status": "error", "message": str(e)})
                self.send_response(client, 500, response, "application/json")
            except:
                pass
    
    def cleanup(self):
        if self.wlan:
            try:
                self.wlan.active(False)
            except:
                pass
        if self.udp_listen_sock:
            try:
                self.udp_listen_sock.close()
            except:
                pass

def enter_ota_mode(dd_id):
    print("\n{}".format('='*40))
    print("  MODE OTA DD{:02d} v{}".format(dd_id, __version__))
    print("{}".format('='*40))
    
    # Nettoyage mémoire agressif AVANT de créer l'objet OTA
    gc.collect()
    
    ota = OTAMode(dd_id)
    
    if not ota.enable_wifi():
        print("[OTA] WiFi fail. Reboot...")
        # Effacer le flag avant de rebooter
        if nvs_utils:
            nvs_utils.set_i32("DTD", "ota_mode", 0)
        time.sleep(3)
        machine.reset()
        return
    
    # Setup UDP listener pour recevoir commandes du TA
    ota.setup_udp_listener()
    
    # Première annonce au démarrage
    ota.announce_to_ta()
    
    try:
        ota.start_ota_server()
    except KeyboardInterrupt:
        print("\n[OTA] Stop")
    finally:
        ota.cleanup()
        # Effacer le flag OTA avant de redémarrer
        if nvs_utils:
            print("[OTA] Effacement flag OTA...")
            nvs_utils.set_i32("DTD", "ota_mode", 0)
        print("[OTA] Reboot...")
        time.sleep(2)
        machine.reset()