import socket
import re
import threading
from threading import Thread
import time

def client_server(socket_client,socket_server):
    while 1:
        m=socket_client.recv(1)
        socket_server.sendall(m)

def server_client(socket_client,socket_server):
    while 1:
        m=socket_server.recv(1)
        socket_client.sendall(m)

def filter(m):
    m = str(m,"utf-8")
    packet = ""
    m = m.splitlines()
    print(m)
    urlSplit1 = re.compile(r'(^.*) HTTP/1.1')
    for i in m:
        if(re.match('(^.*) HTTP/1.1',i)):
            result1 = urlSplit1.search(i)
            part1 = result1.group(1)
            part1+= ' HTTP/1.0'
            packet +=part1 + '\r\n'
            continue
        if(i=="Connection:Keep-alive" or i == "Proxy-Connection: keep-alive" or i == "Accept-Encoding: gzip, deflate"):
            continue
        packet+=i +'\r\n'
    return packet   

#checks if there's forbidden words in the url
def forbidden(address):
    with open(r'keywords.txt', 'r') as file:
            forbidden = False
            lines = file.readlines()
            for line in lines:
                aline = line.strip()
                if aline in address:
                    forbidden = True
                    break
                else:
                    forbidden = False
            return forbidden

#Replace forbidden words in the html page
def replaceforbid(page):
    with open(r'keywords.txt', 'r') as file:
        lines = file.readlines()
        for line in lines:
            aline = line.strip()
            if aline in page:
                page = page.replace(aline,"")
    return page   

#change the title of the page
def changetitle(page):
    re_debut_titre = re.compile(r'<title>(.*)</title>',re.I)
    titre = ""
    resultat = re_debut_titre.search(page)
    titre += resultat.group(1)
    page = page.replace(titre,"Proxy")
    return(page)     


def proxy(socket_client):
    message=socket_client.recv(4044)
    m=message
    message=str(message,'utf8')
    res=message.split();
    if len(res)==0:
        return
    url=res[1]
    if(re.match('http://([a-zA-Z0-9.\-]+):?([0-9]*)([/a-zA-Z0-9/]*)',url)):
        urlSplit1 = re.compile(r'http://([a-zA-Z0-9.\-]+):?([0-9]*)([/a-zA-Z0-9/]*)')
        result1 = urlSplit1.search(url)
        address,port,chemin = result1.groups()
        if address=="detectportal.firefox.com":
            return

        if len(port)==0:
            port="80"
        print(address,port,chemin)
        adresse_serveur = socket.gethostbyname(address)
        print(adresse_serveur)
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        if forbidden(address):
            reply = "HTTP/1.0 403 Forbidden\r\n"
            reply += "Proxy-agent: Pyx\r\n"
            reply += "\r\n"
            with open(r'index.html', 'r') as file:
                lines = file.readlines()
                for line in lines:
                    aline = line.strip()
                    reply += aline
            socket_client.sendall(reply.encode())
        else:
            try: 
                print(port)
                port=int(port)
                socket_server.connect((str(adresse_serveur), port))
            except Exception as e:
                print ("Probleme de connexion", e.args)
            req=filter(m)
            print(m)
            page=b''
            req=bytes(req,'utf8')
            socket_server.sendall(req)
            while 1:
                data = socket_server.recv(4096)
                if not data:
                    break
                page += data
            #page = str(page,'utf8')
            page = replaceforbid(str(page,'utf8'))
            page = bytes(page,'utf8')
            page = changetitle(str(page,'utf8'))
            page = bytes(page,'utf8')
            socket_client.sendall(page)
            socket_client.close()

    else:
        urlSplit2=re.compile(r'([^:]*):?([^:\D/$]*)?[/]?([^$]{0,})?')
        result2=urlSplit2.search(url)
        address,port,chemin=result2.groups()
        print(address)
        adresse_serveur = socket.gethostbyname(address)
        print(adresse_serveur)
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            print(port)
            port=int(port)
            socket_server.connect((str(adresse_serveur), port))
        except Exception as e:
            print ("Probleme de connexion", e.args)
        
        # Connect to port 443
        # If successful, send 200 code response
        reply = "HTTP/1.0 200 Connection established\r\n"
        reply += "Proxy-agent: Pyx\r\n"
        reply += "\r\n"
        socket_client.sendall( reply.encode() )
        
        t = threading.Thread(target = client_server , args=(socket_client,socket_server,))
        t.start()   
        p = threading.Thread(target = server_client , args=(socket_client,socket_server,))
        p.start()
            
        #print(page)
        #print()
        #socket_client.send(page)
        #page=socket_client.recv(2044)
        #print(page)
        #socket_client.send(page)

tsap_proxy=('',6789)

socket_proxy=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
socket_proxy.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
socket_proxy.bind(tsap_proxy)
while 1:
    socket_proxy.listen(socket.SOMAXCONN)
    socket_client,tsap_client=socket_proxy.accept()
    d = threading.Thread(target = proxy , args=(socket_client,))
    d.start()
#done