# /// script
# requires-python = ">=3.10"
# dependencies = [ "fastmcp", "logging" ]
# ///

"""
Copyright (c) 2025 apktool mcp server developer(s) (https://github.com/zinja-coder/apktool-mcp-server)
See the file 'LICENSE' for copying permission
"""

import logging
import subprocess
import os
import shutil

from typing import List, Union, Dict, Optional

from mcp.server.fastmcp import FastMCP

# set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Initialize the MCP Object
mcp = FastMCP("APKTool-MCP Server")

# Current workspace for decoded APK projects
WORKSPACE_DIR = os.environ.get("APKTOOL_WORKSPACE", os.path.join("apktool_mcp_server_workspace"))

# Ensure workspace directory exists
os.makedirs(WORKSPACE_DIR, exists_ok=True)


# Helper function to run APKTool commands
def run_command(command: List[str], timeout: int = 300) -> Dict[str, Union[str, int, bool]]:
    try:
        logger.info(f"Running command: {' '.join(command)}")
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
            timeout=timeout
        )
        logger.info(f"Command completed with return code {result.returncode}")
        return {
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        }
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with return code {e.returncode}: {e.stderr}")
        return {
            "success": False,
            "stdout": e.stdout,
            "stderr": e.stderr,
            "returncode": e.returncode,
            "error": f"Command failed with return code {e.returncode}"
        }
    except subprocess.TimeoutExpired as e:
        logger.error(f"Command timed out after {timeout} seconds")
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds"
        }
    except Exception as e:
        logger.error(f"Error running command: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
    

# MCP Tools

@mcp.tool(name="decode_apk", description="Decode an APK file using APKTool")
async def decode_apk(apk_path: str, force: bool = True, no_res: bool = False, no_src: bool = False) -> Dict:
    """
    Decode an APK file using APKTool, extracting resources and smali code.

    Args:
        apk_path: Path to the APK file to decode
        force: Force delete destination directory if it exists
        no_res: Do not decode resources
        no_src: Do not decode sources
    
    Returns:
        Dictionary with operation results
    """

    if not os.path.exists(apk_path):
        return {"success": False, "error": f"APK file not found: {apk_path}"}
    
    # If output directory not specified, use the APK filename in workspace
    apk_name = os.path.basename(apk_path).rsplit('.',1)[0]
    output_dir = os.path.join(WORKSPACE_DIR, apk_name)

    command = ["apktool", "d", apk_path, "-o", output_dir]

    if force:
        command.append("-f")
    if no_res:
        command.append("-r")
    if no_src:
        command.append("-s")
    
    result = run_command(command)

    if result["success"]:
        result["project_dir"] = output_dir
    
    return result

@mcp.tool(name="build_apk", description="Build an APK file from a decoded APKTool project.")
async def build_apk(project_dir: str, output_apk: Optional[str] = None, debug: bool = True, force_all: bool = False) -> Dict:
    """
    Build an APK file from a decoded APKTool project.

    Args:
        project_dir: Path to the APKTool project directory
        output_dir: Optional output APK path
        debug: Build with debugging info
        force_all: Force rebuild all files
    
    Returns:
        Dictionary with operation results
    """

    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    command = ["apktool", "b", project_dir]

    if debug:
        command.append("-d")
    if force_all:
        command.append("-f")
    if output_apk:
        command.extend(["-o", output_apk])

    result = run_command(command)

    if result["success"]:
        # Determine built APK path if not specified
        if not output_apk:
            output_apk = os.path.join(project_dir, "dist", os.path.basename(project_dir) + ".apk")

        if os.path.exists(output_apk):
            result["apk_path"] = output_apk
        else:
            result["warning"] = f"Build succeeded but APK not found at expected path: {output_apk}"
    
    return result

@mcp.tool(name="get_manifest", description="Get the AndroidManifest.xml content from a decoded APK project.")
async def get_manifest(project_dir: str) -> Dict:
    """
    Get the AndroidManifest.xml content from a decoded APK project.

    Args:
        project_dir: Path to the APKTool project directory

    Returns:
        Dictionary with manifest content or error
    """
    
    manifest_path = os.path.join(project_dir, "AndroidManifest.xml")



# changelog

# removed mcp tool list_workspace_projects
# remove method get direcotry size
# removed method get_package_name_from
# added name and description in all mcp tools
# removed output_dir option from decode apk mcp tool