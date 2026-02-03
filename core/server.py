import sys
import json
import os
import pypdf
import docx
import urllib.parse

# === MCP Server: 文档读取服务器 ===
# 提供读取 PDF, DOCX, TXT, MD 文件内容的工具

def read_pdf(path):
    """读取 PDF 文件内容"""
    try:
        reader = pypdf.PdfReader(path)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
        
        if not text.strip():
            return "PDF 读取成功，但内容为空 (可能是扫描件或加密)。"
        return text
    except Exception as e:
        return f"PDF 读取错误: {str(e)}"

def read_docx(path):
    """读取 DOCX 文件内容"""
    try:
        doc = docx.Document(path)
        text = "\n".join([para.text for para in doc.paragraphs])
        if not text.strip():
            return "DOCX 读取成功，但内容为空。"
        return text
    except Exception as e:
        return f"DOCX 读取错误: {str(e)}"

def read_text_file(path):
    """读取普通文本文件 (.txt, .md, .py, etc.)"""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception as e:
        return f"文本读取错误: {str(e)}"

def read_folder(path, extensions=[".md", ".txt"]):
    """递归读取文件夹下的所有指定后缀文件"""
    combined_text = ""
    file_count = 0
    max_files = 30 # 限制一次最多读取 30 个文件
    max_total_chars = 50000 # 限制总字符数 5万，防止上下文溢出
    
    # 忽略的目录列表
    ignore_dirs = {".git", ".github", "translations", "images", "node_modules", ".devcontainer", "solution"}

    if not os.path.exists(path):
        return f"目录不存在: {path}"
        
    for root, dirs, files in os.walk(path):
        # 修改 dirs 列表以跳过忽略的目录 (必须原地修改)
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            if file_count >= max_files:
                break
            ext = os.path.splitext(file)[1].lower()
            if ext in extensions:
                file_path = os.path.join(root, file)
                content = read_text_file(file_path)
                
                # 检查是否会超出总字符限制
                if len(combined_text) + len(content) > max_total_chars:
                    combined_text += f"\n\n[系统提示] 已达到最大字符数限制 ({max_total_chars})，停止读取更多文件。"
                    return f"已成功读取目录 {path} 下的前 {file_count} 个文件 (因达到字符限制已截断)。\n" + combined_text

                combined_text += f"\n\n=== FILE: {file} ({file_path}) ===\n\n"
                combined_text += content
                file_count += 1
        
        if file_count >= max_files:
            break
    
    if file_count == 0:
        return f"目录 {path} 下没有找到支持的文档文件 ({extensions}) (已忽略 translations 等目录)。"
    
    header = f"已成功读取目录 {path} 下的前 {file_count} 个文件 (总文件数可能更多，但为防止上下文溢出已截断)。\n"
    return header + combined_text

# 定义工具列表
TOOLS = [
    {
        "name": "read_document",
        "description": "读取本地文档内容 (支持 .pdf, .docx, .txt, .md)。用于学习单个文档。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件的本地路径"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "read_folder",
        "description": "递归读取文件夹下的所有文档 (默认支持 .md, .txt)。用于批量学习课程或代码库。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件夹的本地路径"}
            },
            "required": ["path"]
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

    if method == "initialize":
        response["result"] = {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "doc-loader", "version": "1.2"}
        }
    
    elif method == "tools/list":
        response["result"] = {"tools": TOOLS}

    elif method == "tools/call":
        name = params.get("name")
        args = params.get("arguments", {})
        
        if name == "read_document":
            raw_path = args.get("path", "")
            path = raw_path.strip('"').strip("'")
            if not os.path.exists(path):
                decoded_path = urllib.parse.unquote(path)
                if os.path.exists(decoded_path): path = decoded_path
            
            if not os.path.exists(path):
                response["result"] = {"content": [{"type": "text", "text": f"文件不存在: {path}"}]}
            else:
                ext = os.path.splitext(path)[1].lower()
                content = ""
                if ext == ".pdf": content = read_pdf(path)
                elif ext == ".docx": content = read_docx(path)
                else: content = read_text_file(path)
                response["result"] = {"content": [{"type": "text", "text": content}]}

        elif name == "read_folder":
            raw_path = args.get("path", "")
            path = raw_path.strip('"').strip("'")
            if not os.path.exists(path):
                decoded_path = urllib.parse.unquote(path)
                if os.path.exists(decoded_path): path = decoded_path

            content = read_folder(path)
            response["result"] = {"content": [{"type": "text", "text": content}]}
            
        else:
            response["error"] = {"code": -32601, "message": "Method not found"}

    else:
        return None

    return response

def main():
    if sys.platform == 'win32':
        import io
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    for line in sys.stdin:
        try:
            if not line.strip(): continue
            request = json.loads(line)
            response = handle_request(request)
            if response:
                print(json.dumps(response), flush=True)
        except Exception as e:
            sys.stderr.write(f"Error processing request: {e}\n")

if __name__ == "__main__":
    main()
