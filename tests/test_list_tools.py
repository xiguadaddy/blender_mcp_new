import asyncio
import json

async def send_request():
    server_host = "localhost"
    server_port = 27015
    try:
        reader, writer = await asyncio.open_connection(server_host, server_port)

        # 构造 list_tools 请求
        request = {
            "method": "mcp/listTools",
            "params": {}
        }
        message = json.dumps(request)
        writer.write(f"{len(message)}:".encode() + message.encode())
        await writer.drain()

        # 接收响应
        header = b""
        while b":" not in header:
            chunk = await reader.read(1)
            if not chunk:
                return None
            header += chunk

        length = int(header.decode().split(":")[0])
        response_data = b""
        while len(response_data) < length:
            chunk = await reader.read(min(4096, length - len(response_data)))
            if not chunk:
                return None
            response_data += chunk

        response = json.loads(response_data.decode())
        print("Response received:", json.dumps(response, indent=4))

        writer.close()
        await writer.wait_closed()

    except FileNotFoundError:
        print(f"Error: Server not found at {server_host}:{server_port}. Make sure the MCP server is running.")
    except ConnectionRefusedError:
        print(f"Error: Connection refused at {server_host}:{server_port}. Make sure the MCP server is running and listening.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(send_request())
