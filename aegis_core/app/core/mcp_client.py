"""
app/core/mcp_client.py
"""
import sys
import os
from langchain_mcp_adapters.client import MultiServerMCPClient

# 1. Dynamically grab the Python executable from your active virtual environment
python_exe = sys.executable

# 2. Map the exact paths to your isolated server files
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
intel_server_path = os.path.join(base_dir, "mcp_servers", "intel_server.py")
command_server_path = os.path.join(base_dir, "mcp_servers", "command_server.py")
mail_server_path = os.path.join(base_dir, "mcp_servers", "mcp_server_mail.py")

# 3. Configure the secure subprocess connections
aegis_mcp_client = MultiServerMCPClient({
    "intel": {
        "command": python_exe,
        "args": [intel_server_path],
        "transport": "stdio",
    },
    "command": {
        "command": python_exe,
        "args": [command_server_path],
        "transport": "stdio",
    },
    "mail": {
        "command": python_exe,
        "args": [mail_server_path],
        "transport": "stdio",
    }
})