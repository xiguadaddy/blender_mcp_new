import socket
import time

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    host = "127.0.0.1"
    port = 27015
    
    try:
        server_socket.bind((host, port))
        server_socket.listen(1)
        print(f"测试服务器启动，监听 {host}:{port}")
        
        while True:
            try:
                client_socket, addr = server_socket.accept()
                print(f"连接来自: {addr}")
                client_socket.sendall(b"Hello from test server")
                client_socket.close()
            except Exception as e:
                print(f"处理客户端时错误: {e}")
    except Exception as e:
        print(f"启动服务器时错误: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()
