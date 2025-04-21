<div align="center">

# apktool-mcp-server (Part of Zin's Android Rerverse Engineering MCP Suite)

![GitHub contributors apktool-mcp-server](https://img.shields.io/github/contributors/zinja-coder/apktool-mcp-server)
![GitHub all releases](https://img.shields.io/github/downloads/zinja-coder/apktool-mcp-server/total)
![GitHub release (latest by SemVer)](https://img.shields.io/github/downloads/zinja-coder/apktool-mcp-server/latest/total)
![Latest release](https://img.shields.io/github/release/zinja-coder/apktool-mcp-server.svg)
![Python 3.10+](https://img.shields.io/badge/python-3%2E10%2B-blue)
[![License](http://img.shields.io/:license-apache-blue.svg)](http://www.apache.org/licenses/LICENSE-2.0.html)

</div>

<!-- It is a still in early stage of development, so expects bugs, crashes and logical erros.-->

![apktool-mcp-server-banner.png](docs/assets/apktool-mcp-server-banner.png) Image generated using AI tools.

---

## 🤖 What is apktool-mcp-server?

**apktool-mcp-server** is a MCP server for the [Apk Tool](https://github.com/iBotPeaches/apktool) that integrates directly with [Model Context Protocol (MCP)](https://github.com/anthropic/mcp) to provide **live reverse engineering support with LLMs like Claude**.

Think: "Decompile → Context-Aware Code Review → AI Recommendations" — all in real time.

Watch the demo!

[![Watch the video](https://img.youtube.com/vi/-CeOZfhwe1U/0.jpg)](https://www.youtube.com/watch?v=-CeOZfhwe1U)


# Other MCP Servers For Android Reverse Engineering 

 - [JADX-MCP-SERVER](https://github.com/zinja-coder/jadx-ai-mcp)

<!-- Place youtube video -->

## Current MCP Tools

The following MCP tools are available:

**TODO**

---

## 🗒️ Sample Prompts

**TODO**

🔍 Basic Code Understanding

**TODO**

🛡️ Vulnerability Detection

**TODO**

🛠️ Reverse Engineering Helpers

**TODO**

📦 Static Analysis

**TODO**

🤖 AI Code Modification

**TODO**

📄 Documentation & Metadata

**TODO**

---

## 📦 Features

**TODO**

---

## 🛠️ Getting Started 

### 1. Downlaod from Releases: https://github.com/zinja-coder/apktool-mcp-server/releases


```bash
# 0. Download the apktool-mcp-server-<version>.zip
https://github.com/zinja-coder/apktool-mcp-server/releases

# 1. 
unzip apktool-mcp-server-<version>.zip

├apktool-mcp-server/
  ├── apktool_mcp_server.py
  ├── requirements.txt
  ├── README.md
  ├── LICENSE
```bash

# 2. Navigate to apktool-mcp-server directory
cd apktool-mcp-server

# 3. This project uses uv - https://github.com/astral-sh/uv instead of pip for dependency management.
    ## a. Install uv (if you dont have it yet)
curl -LsSf https://astral.sh/uv/install.sh | sh
    ## b. OPTIONAL, if for any reasons, you get dependecy errors in apktool-mcp-server, Set up the environment
uv venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
    ## c. OPTIONAL Install dependencies
uv pip install httpx fastmcp

# The setup for apktool-mcp-server is done.
```

## 🤖 2. Claude Desktop Setup

Make sure Claude Desktop is running with MCP enabled.

For instance, I have used following for Kali Linux: https://github.com/aaddrick/claude-desktop-debian

Configure and add MCP server to LLM file:
```bash
nano ~/.config/Claude/claude_desktop_config.json
```
And following content in it:
```json
{
    "mcpServers": {
        "apktool-mcp-server": {
            "command": "/<path>/<to>/uv", 
            "args": [
                "--directory",
                "</PATH/TO/>apktool-mcp-server/",
                "run",
                "apktool_mcp_server.py"
            ]
        }
    }
}
```

Then, navigate code and interact via real-time code review prompts using the built-in integration.

## To report bugs, issues, feature suggestion, Performance issue, general question, Documentation issue.
 - Kindly open an issue with respective template.

 - Tested on Claude Desktop Client, support for other AI will be tested soon!

## 🙏 Credits

This project is a MCP Server for [Apktool](https://github.com/iBotPeaches/apktool), an amazing open-source Android reverse engineering tool created and maintained by [@iBotPeaches](https://github.com/iBotPeaches). All core APK decoding and resource processing logic belongs to them. I have only extended it to support my MCP server with AI capabilities.

[📎 Original README (Apktool)](https://github.com/iBotPeaches/apktool)

The original README.md from Apktool is included here in this repository for reference and credit.

Also huge thanks to [@aaddrick](https://github.com/aaddrick) for developing Claude desktop for Debian based Linux.

And in last, thanks to [@anthropics](https://github.com/anthropics) for developing the Model Context Protocol and [@FastMCP](https://github.com/jlowin/fastmcp) team.

## 📄 License

apktool-mcp-server and all related projects inherits the Apache 2.0 

## ⚖️ Legal Warning

**Disclaimer**

The tools `apktool-mcp-server` and all related tools under this project are intended strictly for educational, research, and ethical security assessment purposes. They are provided "as-is" without any warranties, expressed or implied. Users are solely responsible for ensuring that their use of these tools complies with all applicable laws, regulations, and ethical guidelines.

By using `apktool-mcp-server`, you agree to use them only in environments you are authorized to test, such as applications you own or have explicit permission to analyze. Any misuse of these tools for unauthorized reverse engineering, infringement of intellectual property rights, or malicious activity is strictly prohibited.

The developers of `apktool-mcp-server` shall not be held liable for any damage, data loss, legal consequences, or other consequences resulting from the use or misuse of these tools. Users assume full responsibility for their actions and any impact caused by their usage.

Use responsibly. Respect intellectual property. Follow ethical hacking practices.

---

Built with ❤️ for the reverse engineering and AI communities.
