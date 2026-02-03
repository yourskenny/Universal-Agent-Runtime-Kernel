import sys
import json
import os

# === MCP Server: 文件系统服务器 ===
# 这是一个简化的 MCP (Model Context Protocol) 服务器实现
# 它通过标准输入输出 (Stdio) 与 Agent 通信

def list_files(args):
    path = args.get("path", ".")
    try:
        files = os.listdir(path)
        return {"content": [{"type": "text", "text": json.dumps(files)}]}
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

def read_file(args):
    filename = args.get("filename")
    if not filename:
        return {"isError": True, "content": [{"type": "text", "text": "Missing filename"}]}
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"content": [{"type": "text", "text": content}]}
    except Exception as e:
        return {"isError": True, "content": [{"type": "text", "text": str(e)}]}

# 定义工具列表 (Capabilities)
TOOLS = [
    {
        "name": "list_files",
        "description": "列出目录下的文件",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目录路径"}
            }
        }
    },
    {
        "name": "read_file",
        "description": "读取文件内容",
        "inputSchema": {
            "type": "object",
            "properties": {
                "filename": {"type": "string", "description": "文件名"}
            },
            "required": ["filename"]
        }
    }
]

def handle_request(request):
    method = request.get("method")
    params = request.get("params", {})
    msg_id = request.get("id")

    response = {
        "jsonrpc": "2.0",
        "id": msg_id
    }

    # 1. 初始化握手
    if method == "initialize":
        response["result"] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "my-local-files",
                "version": "1.0"
            }
        }
    
    # 2. 列出可用工具
    elif method == "tools/list":
        response["result"] = {
            "tools": TOOLS
        }

    # 3. 调用工具
    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        
        if name == "list_files":
            result = list_files(args)
            response["result"] = result
        elif name == "read_file":
            result = read_file(args)
            response["result"] = result
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}

    else:
        # 忽略其他通知或不支持的方法
        return None

    return response

def main():
    # 循环读取标准输入 (JSON-RPC)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            response = handle_request(request)
            if response:
                print(json.dumps(response), flush=True)
        except Exception as e:
            # 简单的错误处理
            sys.stderr.write(f"Error processing line: {e}\n")

if __name__ == "__main__":
    main()
