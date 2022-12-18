from http.server import BaseHTTPRequestHandler, HTTPServer
import time
import logging
from io import BytesIO
import json

host = "localhost"
port = 8888

class ConfigProxyInterface(BaseHTTPRequestHandler):
    def do_GET(self):
        f = open("config.json", "r")
        config_data_dict = json.loads(f.read())
        f.close()
        filter_choice = config_data_dict["filter_choice"]
        forbidden_keywords = config_data_dict["forbidden_keywords"]
        
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open("web.html", "r") as f:
            html_contents = f.readlines()
        if filter_choice == "deactivate_filter":
            html_contents[10], html_contents[11] = html_contents[11], html_contents[10]
        if len(forbidden_keywords) > 0:
            temp = html_contents[17].split("><")
            temp[0] += ">"
            temp[1] = "<" + temp[1]
            words = ""
            for w in forbidden_keywords:
                words += w + "&#13;&#10"
            html_contents[17] = temp[0] + words + temp[1]
        for l in html_contents:
            self.wfile.write(bytes(l, "utf-8"))

    def do_POST(self):
        content_length = self.headers['Content-Length']
        if content_length and content_length != '0':
            try:
                body = self.rfile.read(int(content_length))
                config_data = body.decode().split('&')
                config_data_dict = {}
                for entry in config_data:
                    key, value = entry.split("=", 1)
                    if key == "forbidden_keywords":
                        value = value.split("%0D%0A")
                        value = list(filter(lambda a: len(a) > 0, value))
                    config_data_dict[key] = value
                config_data_json = json.dumps(config_data_dict, indent=4)
                print("Config data in JSON format:")
                print(config_data_json)
                with open("config.json", "w") as f:
                    f.write(config_data_json)
                resp_msg = 'Proxy configuration saved!'
            except Exception as e:
                resp_msg = "Submission problem:" + str(e.args)
                print(resp_msg)
                return
        else:
            resp_msg = "No data was submitted"
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.send_header('Content-length', len(resp_msg))
        self.end_headers()
        response = BytesIO()
        response.write(b'Proxy configuration saved!\n')
        response.write(bytes(str(config_data_json), "utf-8"))
        self.wfile.write(response.getvalue())

if __name__ == "__main__":         
    webServer = HTTPServer((host, port), ConfigProxyInterface)
    print("Proxy configuration server listening at http://%s:%s" % (host, port))

    try:
        webServer.serve_forever()
    except KeyboardInterrupt:
        pass

    webServer.server_close()