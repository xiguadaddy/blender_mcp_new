import socket

def main():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    host = "127.0.0.1"
    port = 27015
    
    try:
        print(f"尝试连接到 {host}:{port}...")
        client_socket.connect((host, port))
        data = client_socket.recv(1024)
        print(f"收到数据: {data.decode()}")
    except Exception as e:
        print(f"连接时错误: {e}")
    finally:
        client_socket.close()

if __name__ == "__main__":
    main()
