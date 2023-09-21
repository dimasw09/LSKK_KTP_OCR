from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

# FTP Server setup
authorizer = DummyAuthorizer()
authorizer.add_user("dimassk7", "12345", "F:\KerjaPraktik\KTP-SCAN1\envktp", perm="elradfmw")

ftp_handler = FTPHandler
ftp_handler.authorizer = authorizer

ftp_server = FTPServer(("192.168.1.72", 2121), ftp_handler)

def run_ftp_server():
    print("FTP Server berjalan")
    ftp_server.serve_forever()

if __name__ == "__main__":
    run_ftp_server()
