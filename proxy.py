import socket
import sys
import re
import threading
import json
import time
from threading import Thread
from config_interface import ConfigProxyInterface
from http.server import HTTPServer

memo={}
nb_of_visits={}

# Forward data stream from one socket to another
def forward(socket_source: socket.socket, socket_dest: socket.socket) -> None:
    while 1:
        stream_data = socket_source.recv(1)
        socket_dest.sendall(stream_data)

# Check if the url contains forbidden words
def forbidden(address: str) -> bool:
    with open('config.json', 'r') as file:
        config_data_dict = json.loads(file.read())
        forbidden_keywords = config_data_dict["forbidden_keywords"]
        forbidden = False
        for w in forbidden_keywords:
            aline = w.strip()
            if aline in address:
                forbidden = True
                break
    return forbidden

# Replace forbidden words in the content of the HTML page
def replaceforbid(page):
    with open('config.json', 'r') as file:
        config_data_dict = json.loads(file.read())
        forbidden_keywords = config_data_dict["forbidden_keywords"]
        for w in forbidden_keywords:
            aline = w.strip()
            if aline.casefold().lower() in page.lower():
                page = page.replace(aline,"*" * len(aline))
    return page 

# Change the title of the page
def chgTitle(page):
    page=page.splitlines()
    p=''
    re_debut_titre = re.compile(r'(.*)<title>(.*)</title>(.*)',re.I)
    for line in page:
        if re_debut_titre.match(line):
            resultat = re_debut_titre.search(line)
            line = '<title>Proxy</title>'
        p+=line+'\n'
    return p

def filter(msg):
    packet = ""
    msg = msg.splitlines()
    print(msg)
    urlSplit = re.compile(r'(^.*) HTTP/1.1')

    for i in msg:
        if(re.match('(^.*) HTTP/1.1',i)):
            result1 = urlSplit.search(i)
            part1 = result1.group(1)
            part1+= ' HTTP/1.0'
            packet +=part1 + '\r\n'
            continue
        if(i=="Connection: keep-alive" or i == "Proxy-Connection: keep-alive" or i == "Accept-Encoding: gzip, deflate"):
            continue
        packet+=i +'\r\n'
    return packet  
        
def proxy(socket_client: socket.socket) -> None:
    # cache_memory = {}

    with open("config.json", "r") as file:
        config_data_dict = json.loads(file.read())
        filter_choice = config_data_dict["filter_choice"]

    msg = socket_client.recv(2044) # Why 4044?
    if not msg:
        return
    msg = msg.decode()
    res = msg.split()

    if len(res) == 0:
        return
    print(repr(msg))

    url = res[1]

    rx_pattern = r'http://([a-zA-Z0-9.\-]+):?([0-9]*)(.*)'

    # In case HTTP protocol was used
    if re.match(rx_pattern, url):
        urlSplit = re.compile(rx_pattern)
        result = urlSplit.search(url)
        address, port, chemin = result.groups()
        resp = b''

        if forbidden(address) and filter_choice == "activate_filter":
            reply = "HTTP/1.0 403 Forbidden\r\n"
            reply += "Proxy-agent: Pyx\r\n"
            reply += "\r\n"
            with open('index.html', 'r') as file:
                lines = file.readlines()
                for line in lines:
                    aline = line.strip()
                    reply += aline
            socket_client.sendall(reply.encode())
            socket_client.close()
        else:
            if address + chemin in memo.keys():
                response=bytes(memo[address+chemin],'utf8')
                socket_client.sendall(response)
                socket_client.close()
            else: 
                if len(port)==0:
                    port="80"
                adresse_serveur = socket.gethostbyname(address)
                # if address in memo.keys():
                #     socket_client.sendall(memo[address])
                # else:
                print("Fetch")
                socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
                try:
                    port = int(port)
                    socket_server.connect((adresse_serveur, port))
                except Exception as e:
                    print("Probleme de connexion", e.args)
                req = filter(msg)
                page = b''
                req = bytes(req, 'utf-8')
                socket_server.sendall(req)
                while 1:
                    data = socket_server.recv(4096)
                    if not data:
                        break
                    page += data

                if b'Content-Type: text/html' in page:
                    page = page.decode()
                    if filter_choice == "activate_filter":
                        page = replaceforbid(page)
                    page = chgTitle(page)
                    page = bytes(page,'utf8')
                socket_client.sendall(page)
                socket_client.close()

                try:
                    updateVisits=open("nbVisits.txt",'w')
                except Exception as e:
                    print(e.args)
                    sys.exit(1)

                if address+chemin not in memo.keys():
                    if address+chemin in nb_of_visits.keys():
                        if nb_of_visits[address+chemin] >= 5:
                            try:
                                memoAdd=open('urls.txt','a+')
                            except Exception as e:
                                print(e.args)
                                sys.exit(1)
                            memoAdd.write('\n'+address+chemin+':'+str(page,'utf8'))
                            memoAdd.write('\nend')
                            memoAdd.close()
                        nb_of_visits[address+chemin]+=1
                        for site in nb_of_visits.keys():
                            updateVisits.write(site+":"+str(nb_of_visits[site])+'\n')
                        updateVisits.close()
                    else:
                        nb_of_visits[address+chemin]=1
                        for site in nb_of_visits.keys():
                            updateVisits.write(site+":"+str(nb_of_visits[site])+'\n')

    # In case HTTPS Protocol was used
    else:
        urlSplit = re.compile(r'([^:]*):?([^:\D/$]*)?[/]?([^$]{0,})?')
        result = urlSplit.search(url)
        address, port, chemin = result.groups()

        if forbidden(address):
            reply = "HTTP/1.0 403 Forbidden\r\n"
            reply += "Proxy-agent: Mozilla/5.0\r\n\r\n"
            reply += "\r\n"
            socket_client.sendall(reply.encode())
        else:
            adresse_serveur = socket.gethostbyname(address)
            socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
            try:
                port = int(port)
                socket_server.connect((str(adresse_serveur), port))
            except Exception as e:
                print ("Probleme de connexion", e.args)
                sys.exit(1)
            # Connect to port 443
            # If successful, send 200 code response
            reply = "HTTP/1.0 200 Connection established\r\n"
            reply += "Proxy-agent: Mozilla/5.0\r\n"
            reply += "\r\n"
            socket_client.sendall(bytes(reply, "utf-8"))


            client_to_server_thread = threading.Thread(target=forward, args=(socket_client, socket_server,))
            client_to_server_thread.start()

            server_to_client_thread = threading.Thread(target=forward, args=(socket_server, socket_client,))
            server_to_client_thread.start()

def run_config_server():
    config_server_host = 'localhost'
    config_server_port = 8888
    webServer = HTTPServer((config_server_host, config_server_port), ConfigProxyInterface)
    print("Proxy configuration server listening at http://%s:%s" % ('localhost', 8888))
    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass
    webServer.server_close()            

response=''
url=''

try:
    visitedSites=open("nbVisits.txt",'r')

except Exception as e:
    print(e.args)
    sys.exit(1)

while 1:
    ligne=visitedSites.readline()
    if not ligne:
        break
    l=ligne.split(':')
    nb_of_visits[l[0]]=int(l[1])

visitedSites.close()

try:
    memoRead=open('urls.txt','r')
except Exception as e:
    print(e.args)
    sys.exit(1)
memoRead.readline()

while 1:
    ligne=memoRead.readline()
    if not ligne:
        break
    lig=ligne
    if ligne=='end\n':
         continue
    ligne=ligne.split(':')
    url=ligne[0]
    #print(url)
    memo[url]=ligne[1]
    while 1:
        l=memoRead.readline()
        if l == 'end\n' or l=='end':
            break
        response+=l
    if len(url)!=0:
        memo[url]+=response
    response=''
memoRead.close()

config_sv_thread = threading.Thread(target=run_config_server)
config_sv_thread.start()

tsap_proxy = ('', 6789)
socket_proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
socket_proxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_proxy.bind(tsap_proxy)
socket_proxy.listen(socket.SOMAXCONN)

while 1:
    (socket_client, client_tsap) = socket_proxy.accept()
    print("New connection from", client_tsap)
    new_thread = threading.Thread(target=proxy, args=(socket_client,))
    new_thread.start()
