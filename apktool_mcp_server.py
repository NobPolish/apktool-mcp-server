# /// script
# dependencies = [ "fastmcp", "logging" ]
# ///

import logging
import subprocess
import os
import json
import shutil
from pathlib import Path
from typing import List, Union, Dict, Optional

from mcp.server.fastmcp import FastMCP


# Set up logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Console handler for logging to the console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(console_handler)

# Initialize the MCP server
mcp = FastMCP("APKTool-MCP Server")

# Current workspace for decoded APK projects
WORKSPACE_DIR = os.environ.get("APKTOOL_WORKSPACE", os.path.expanduser("~/apktool_workspace"))

# Ensure workspace directory exists
os.makedirs(WORKSPACE_DIR, exist_ok=True)


# Helper function to run APKTool commands
def run_command(command: List[str], timeout: int = 300) -> Dict[str, Union[str, int, bool]]:
    """Run a command and return the result."""
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


# Specific MCP tools for APKTool

@mcp.tool(name="decode_apk", description="Decode an APK file using APKTool")
async def decode_apk(apk_path: str, output_dir: Optional[str] = None, force: bool = True, no_res: bool = False, no_src: bool = False) -> Dict:
    """
    Decode an APK file using APKTool, extracting resources and smali code.
    
    Args:
        apk_path: Path to the APK file to decode
        output_dir: Optional output directory (defaults to APK filename in workspace)
        force: Force delete destination directory if it exists
        no_res: Do not decode resources
        no_src: Do not decode sources
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(apk_path):
        return {"success": False, "error": f"APK file not found: {apk_path}"}
    
    # If output directory not specified, use the APK filename in workspace
    if not output_dir:
        apk_name = os.path.basename(apk_path).rsplit('.', 1)[0]
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


@mcp.tool()
async def build_apk(project_dir: str, output_apk: Optional[str] = None, debug: bool = True, force_all: bool = False) -> Dict:
    """
    Build an APK file from a decoded APKTool project.
    
    Args:
        project_dir: Path to the APKTool project directory
        output_apk: Optional output APK path
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


@mcp.tool()
async def list_workspace_projects() -> Dict:
    """
    List all APKTool project directories in the workspace.
    
    Returns:
        Dictionary with list of project directories
    """
    try:
        if not os.path.exists(WORKSPACE_DIR):
            return {"success": True, "projects": [], "workspace": WORKSPACE_DIR}
        
        projects = []
        for item in os.listdir(WORKSPACE_DIR):
            project_path = os.path.join(WORKSPACE_DIR, item)
            if os.path.isdir(project_path):
                manifest_path = os.path.join(project_path, "AndroidManifest.xml")
                apktool_yml_path = os.path.join(project_path, "apktool.yml")
                
                # Check if this looks like an APKTool project
                if os.path.exists(manifest_path) or os.path.exists(apktool_yml_path):
                    project_info = {
                        "name": item,
                        "path": project_path,
                        "has_manifest": os.path.exists(manifest_path),
                        "has_apktool_yml": os.path.exists(apktool_yml_path),
                        "size_mb": round(get_directory_size(project_path) / (1024 * 1024), 2)
                    }
                    
                    # Try to get package name from manifest
                    if project_info["has_manifest"]:
                        package_name = get_package_name_from_manifest(manifest_path)
                        if package_name:
                            project_info["package_name"] = package_name
                    
                    projects.append(project_info)
        
        return {
            "success": True, 
            "projects": projects, 
            "workspace": WORKSPACE_DIR,
            "count": len(projects)
        }
    except Exception as e:
        logger.error(f"Error listing workspace projects: {str(e)}")
        return {"success": False, "error": f"Failed to list projects: {str(e)}"}


def get_directory_size(path: str) -> int:
    """Calculate the total size of a directory in bytes."""
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


def get_package_name_from_manifest(manifest_path: str) -> Optional[str]:
    """Extract package name from AndroidManifest.xml."""
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_content = f.read()
            import re
            package_match = re.search(r'package="([^"]+)"', manifest_content)
            if package_match:
                return package_match.group(1)
    except Exception as e:
        logger.error(f"Error extracting package name: {str(e)}")
    return None


@mcp.tool()
async def get_manifest(project_dir: str) -> Dict:
    """
    Get the AndroidManifest.xml content from a decoded APK project.
    
    Args:
        project_dir: Path to the APKTool project directory
    
    Returns:
        Dictionary with manifest content or error
    """
    manifest_path = os.path.join(project_dir, "AndroidManifest.xml")
    
    if not os.path.exists(manifest_path):
        return {"success": False, "error": f"AndroidManifest.xml not found in {project_dir}"}
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "manifest": content, "path": manifest_path}
    except Exception as e:
        logger.error(f"Error reading manifest: {str(e)}")
        return {"success": False, "error": f"Failed to read AndroidManifest.xml: {str(e)}"}


@mcp.tool()
async def get_apktool_yml(project_dir: str) -> Dict:
    """
    Get apktool.yml information from a decoded APK project.
    
    Args:
        project_dir: Path to the APKTool project directory
    
    Returns:
        Dictionary with apktool.yml content or error
    """
    yml_path = os.path.join(project_dir, "apktool.yml")
    
    if not os.path.exists(yml_path):
        return {"success": False, "error": f"apktool.yml not found in {project_dir}"}
    
    try:
        with open(yml_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"success": True, "content": content, "path": yml_path}
    except Exception as e:
        logger.error(f"Error reading apktool.yml: {str(e)}")
        return {"success": False, "error": f"Failed to read apktool.yml: {str(e)}"}


@mcp.tool()
async def list_smali_directories(project_dir: str) -> Dict:
    """
    List all smali directories in a project.
    
    Args:
        project_dir: Path to the APKTool project directory
    
    Returns:
        Dictionary with list of smali directories
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        smali_dirs = [d for d in os.listdir(project_dir) 
                      if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        
        return {
            "success": True, 
            "smali_dirs": smali_dirs,
            "count": len(smali_dirs)
        }
    except Exception as e:
        logger.error(f"Error listing smali directories: {str(e)}")
        return {"success": False, "error": f"Failed to list smali directories: {str(e)}"}


@mcp.tool()
async def list_smali_files(project_dir: str, smali_dir: str = "smali", package_prefix: Optional[str] = None) -> Dict:
    """
    List smali files in a specific smali directory, optionally filtered by package prefix.
    
    Args:
        project_dir: Path to the APKTool project directory
        smali_dir: Which smali directory to use (smali, smali_classes2, etc.)
        package_prefix: Optional package prefix to filter by (e.g., "com.example")
    
    Returns:
        Dictionary with list of smali files
    """
    smali_path = os.path.join(project_dir, smali_dir)
    
    if not os.path.exists(smali_path):
        smali_dirs = [d for d in os.listdir(project_dir) 
                      if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        return {
            "success": False, 
            "error": f"Smali directory not found: {smali_path}",
            "available_dirs": smali_dirs
        }
    
    try:
        smali_files = []
        package_path = None
        
        if package_prefix:
            # If package prefix is given, convert it to directory path
            package_path = os.path.join(smali_path, package_prefix.replace('.', os.path.sep))
            if not os.path.exists(package_path):
                return {
                    "success": False,
                    "error": f"Package not found: {package_prefix}",
                    "expected_path": package_path
                }
            
            root_dir = package_path
        else:
            root_dir = smali_path
        
        # Recursively find all .smali files
        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".smali"):
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, smali_path)
                    class_name = rel_path.replace(os.path.sep, '.').replace('.smali', '')
                    
                    smali_files.append({
                        "class_name": class_name,
                        "file_path": file_path,
                        "rel_path": rel_path
                    })
        
        # Sort by class name
        smali_files.sort(key=lambda x: x["class_name"])
        
        return {
            "success": True, 
            "smali_files": smali_files,
            "count": len(smali_files),
            "smali_dir": smali_dir,
            "package_prefix": package_prefix
        }
    except Exception as e:
        logger.error(f"Error listing smali files: {str(e)}")
        return {"success": False, "error": f"Failed to list smali files: {str(e)}"}


@mcp.tool()
async def get_smali_file(project_dir: str, class_name: str) -> Dict:
    """
    Get content of a specific smali file by class name.
    
    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)
    
    Returns:
        Dictionary with smali file content
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        # Look for the class in all smali directories
        smali_dirs = [d for d in os.listdir(project_dir) 
                      if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        
        for smali_dir in smali_dirs:
            file_path = os.path.join(project_dir, smali_dir, class_name.replace('.', os.path.sep) + '.smali')
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return {
                    "success": True,
                    "content": content,
                    "file_path": file_path,
                    "smali_dir": smali_dir
                }
        
        return {
            "success": False,
            "error": f"Smali file not found for class: {class_name}",
            "searched_dirs": smali_dirs
        }
    except Exception as e:
        logger.error(f"Error getting smali file: {str(e)}")
        return {"success": False, "error": f"Failed to get smali file: {str(e)}"}


@mcp.tool()
async def modify_smali_file(project_dir: str, class_name: str, new_content: str, create_backup: bool = True) -> Dict:
    """
    Modify the content of a specific smali file.
    
    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)
        new_content: New content for the smali file
        create_backup: Whether to create a backup of the original file
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        # Look for the class in all smali directories
        smali_dirs = [d for d in os.listdir(project_dir) 
                      if d.startswith("smali") and os.path.isdir(os.path.join(project_dir, d))]
        
        file_path = None
        for smali_dir in smali_dirs:
            test_path = os.path.join(project_dir, smali_dir, class_name.replace('.', os.path.sep) + '.smali')
            if os.path.exists(test_path):
                file_path = test_path
                break
        
        if not file_path:
            return {
                "success": False,
                "error": f"Smali file not found for class: {class_name}",
                "searched_dirs": smali_dirs
            }
        
        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = file_path + ".bak"
            shutil.copy2(file_path, backup_path)
        
        # Write new content
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"Successfully modified {file_path}",
            "file_path": file_path,
            "backup_path": backup_path
        }
    except Exception as e:
        logger.error(f"Error modifying smali file: {str(e)}")
        return {"success": False, "error": f"Failed to modify smali file: {str(e)}"}


@mcp.tool()
async def list_resources(project_dir: str, resource_type: Optional[str] = None) -> Dict:
    """
    List resources in a project, optionally filtered by resource type.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Optional resource type to filter by (e.g., "layout", "drawable")
    
    Returns:
        Dictionary with list of resources
    """
    res_path = os.path.join(project_dir, "res")
    
    if not os.path.exists(res_path):
        return {"success": False, "error": f"Resources directory not found: {res_path}"}
    
    try:
        if resource_type:
            # List resources of specific type
            type_path = os.path.join(res_path, resource_type)
            if not os.path.exists(type_path):
                resource_types = [d for d in os.listdir(res_path) if os.path.isdir(os.path.join(res_path, d))]
                return {
                    "success": False,
                    "error": f"Resource type directory not found: {resource_type}",
                    "available_types": resource_types
                }
            
            resources = []
            for item in os.listdir(type_path):
                item_path = os.path.join(type_path, item)
                if os.path.isfile(item_path):
                    resources.append({
                        "name": item,
                        "path": item_path,
                        "size": os.path.getsize(item_path)
                    })
            
            return {
                "success": True,
                "resource_type": resource_type,
                "resources": resources,
                "count": len(resources)
            }
        else:
            # List all resource types
            resource_types = []
            for item in os.listdir(res_path):
                type_path = os.path.join(res_path, item)
                if os.path.isdir(type_path):
                    resource_count = len([f for f in os.listdir(type_path) if os.path.isfile(os.path.join(type_path, f))])
                    resource_types.append({
                        "type": item,
                        "path": type_path,
                        "count": resource_count
                    })
            
            return {
                "success": True,
                "resource_types": resource_types,
                "count": len(resource_types)
            }
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        return {"success": False, "error": f"Failed to list resources: {str(e)}"}


@mcp.tool()
async def get_resource_file(project_dir: str, resource_type: str, resource_name: str) -> Dict:
    """
    Get content of a specific resource file.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Resource type (e.g., "layout", "drawable")
        resource_name: Name of the resource file
    
    Returns:
        Dictionary with resource file content
    """
    resource_path = os.path.join(project_dir, "res", resource_type, resource_name)
    
    if not os.path.exists(resource_path):
        return {"success": False, "error": f"Resource file not found: {resource_path}"}
    
    try:
        with open(resource_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "success": True,
            "content": content,
            "path": resource_path,
            "size": os.path.getsize(resource_path)
        }
    except UnicodeDecodeError:
        # This might be a binary resource
        return {
            "success": False,
            "error": "This appears to be a binary resource file and cannot be read as text",
            "path": resource_path,
            "size": os.path.getsize(resource_path),
            "is_binary": True
        }
    except Exception as e:
        logger.error(f"Error getting resource file: {str(e)}")
        return {"success": False, "error": f"Failed to get resource file: {str(e)}"}


@mcp.tool()
async def modify_resource_file(project_dir: str, resource_type: str, resource_name: str, new_content: str, create_backup: bool = True) -> Dict:
    """
    Modify the content of a specific resource file.
    
    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Resource type (e.g., "layout", "values")
        resource_name: Name of the resource file
        new_content: New content for the resource file
        create_backup: Whether to create a backup of the original file
    
    Returns:
        Dictionary with operation results
    """
    resource_path = os.path.join(project_dir, "res", resource_type, resource_name)
    
    if not os.path.exists(resource_path):
        return {"success": False, "error": f"Resource file not found: {resource_path}"}
    
    try:
        # Create backup if requested
        backup_path = None
        if create_backup:
            backup_path = resource_path + ".bak"
            shutil.copy2(resource_path, backup_path)
        
        # Write new content
        with open(resource_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"Successfully modified {resource_path}",
            "path": resource_path,
            "backup_path": backup_path
        }
    except Exception as e:
        logger.error(f"Error modifying resource file: {str(e)}")
        return {"success": False, "error": f"Failed to modify resource file: {str(e)}"}


@mcp.tool()
async def search_in_files(project_dir: str, search_pattern: str, file_extensions: List[str] = [".smali", ".xml"], max_results: int = 100) -> Dict:
    """
    Search for a pattern in files with specified extensions.
    
    Args:
        project_dir: Path to the APKTool project directory
        search_pattern: Text pattern to search for
        file_extensions: List of file extensions to search in
        max_results: Maximum number of results to return
    
    Returns:
        Dictionary with search results
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        results = []
        
        for root, _, files in os.walk(project_dir):
            for file in files:
                if len(results) >= max_results:
                    break
                
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if search_pattern in content:
                                rel_path = os.path.relpath(file_path, project_dir)
                                results.append({
                                    "file": rel_path,
                                    "path": file_path
                                })
                    except UnicodeDecodeError:
                        # Skip binary files
                        pass
                    except Exception as e:
                        logger.error(f"Error reading file {file_path}: {str(e)}")
        
        return {
            "success": True,
            "results": results,
            "count": len(results),
            "max_reached": len(results) >= max_results,
            "search_pattern": search_pattern,
            "file_extensions": file_extensions
        }
    except Exception as e:
        logger.error(f"Error searching in files: {str(e)}")
        return {"success": False, "error": f"Failed to search in files: {str(e)}"}


@mcp.tool()
async def check_apktool_version() -> Dict:
    """
    Check the installed APKTool version.
    
    Returns:
        Dictionary with APKTool version information
    """
    return run_command(["apktool", "--version"])


@mcp.tool()
async def sign_apk(apk_path: str, output_path: Optional[str] = None, keystore_path: Optional[str] = None, 
                  keystore_pass: Optional[str] = None, key_alias: Optional[str] = None, key_pass: Optional[str] = None) -> Dict:
    """
    Sign an APK file.
    
    Args:
        apk_path: Path to the unsigned APK file
        output_path: Optional path for the signed APK
        keystore_path: Path to keystore file (uses debug.keystore if not specified)
        keystore_pass: Keystore password (uses "android" if not specified)
        key_alias: Key alias (uses "androiddebugkey" if not specified)
        key_pass: Key password (uses keystore_pass if not specified)
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(apk_path):
        return {"success": False, "error": f"APK file not found: {apk_path}"}
    
    # If output path not specified, use input name with -signed suffix
    if not output_path:
        output_path = apk_path.rsplit('.', 1)[0] + "-signed.apk"
    
    # Use debug keystore if not specified
    if not keystore_path:
        keystore_path = os.path.expanduser("~/.android/debug.keystore")
        
        # If debug keystore doesn't exist, try to find it in common locations
        if not os.path.exists(keystore_path):
            common_locations = [
                os.path.expanduser("~/.android/debug.keystore"),
                os.path.expanduser("~/android/debug.keystore"),
                os.path.expanduser("~/debug.keystore"),
                "debug.keystore"
            ]
            
            for location in common_locations:
                if os.path.exists(location):
                    keystore_path = location
                    break
            else:
                return {
                    "success": False,
                    "error": "Debug keystore not found. Please specify a keystore path."
                }
    
    # Default values for debug keystore
    if not keystore_pass:
        keystore_pass = "android"
    if not key_alias:
        key_alias = "androiddebugkey"
    if not key_pass:
        key_pass = keystore_pass
    
    try:
        # First try to align the APK
        aligned_apk = apk_path.rsplit('.', 1)[0] + "-aligned.apk"
        align_result = run_command(["zipalign", "-p", "4", apk_path, aligned_apk])
        
        if align_result["success"]:
            input_apk = aligned_apk
        else:
            logger.warning("zipalign failed or not available, continuing with original APK")
            input_apk = apk_path
        
        # Sign the APK
        sign_command = [
            "apksigner", "sign",
            "--ks", keystore_path,
            "--ks-pass", f"pass:{keystore_pass}",
            "--ks-key-alias", key_alias,
            "--key-pass", f"pass:{key_pass}",
            "--out", output_path,
            input_apk
        ]
        
        sign_result = run_command(sign_command)
        
        # Clean up aligned APK if it was created
        if align_result["success"] and os.path.exists(aligned_apk):
            os.remove(aligned_apk)
        
        if sign_result["success"]:
            sign_result["signed_apk_path"] = output_path
            
            # Verify the signed APK
            verify_result = run_command(["apksigner", "verify", "--verbose", output_path])
            sign_result["verify_result"] = verify_result
        
        return sign_result
    except Exception as e:
        logger.error(f"Error signing APK: {str(e)}")
        return {"success": False, "error": f"Failed to sign APK: {str(e)}"}


@mcp.tool()
async def install_apk(apk_path: str, device_id: Optional[str] = None) -> Dict:
    """
    Install an APK on a connected device using ADB.
    
    Args:
        apk_path: Path to the APK file to install
        device_id: Optional device ID for multiple connected devices
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(apk_path):
        return {"success": False, "error": f"APK file not found: {apk_path}"}
    
    command = ["adb"]
    
    if device_id:
        command.extend(["-s", device_id])
    
    command.extend(["install", "-r", apk_path])
    
    return run_command(command)


@mcp.tool()
async def extract_dex(project_dir: str, output_dir: Optional[str] = None) -> Dict:
    """
    Extract DEX files from original APK (if available in project).
    
    Args:
        project_dir: Path to the APKTool project directory
        output_dir: Optional directory to extract DEX files to
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    # Check if original APK is available
    original_dir = os.path.join(project_dir, "original")
    if not os.path.exists(original_dir):
        return {"success": False, "error": f"Original directory not found in project: {original_dir}"}
    
    # Find original APK
    apk_path = None
    for item in os.listdir(original_dir):
        if item.endswith(".apk"):
            apk_path = os.path.join(original_dir, item)
            break
    
    if not apk_path:
        return {"success": False, "error": "Original APK not found in project"}
    
    # If output directory not specified, use project directory
    if not output_dir:
        output_dir = os.path.join(project_dir, "dex")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    try:
        # Use unzip to extract DEX files
        command = ["unzip", "-o", apk_path, "*.dex", "-d", output_dir]
        result = run_command(command)
        
        if result["success"]:
            # List extracted DEX files
            dex_files = [f for f in os.listdir(output_dir) if f.endswith(".dex")]
            result["dex_files"] = dex_files
            result["count"] = len(dex_files)
            result["output_dir"] = output_dir
        
        return result
    except Exception as e:
        logger.error(f"Error extracting DEX files: {str(e)}")
        return {"success": False, "error": f"Failed to extract DEX files: {str(e)}"}


@mcp.tool()
async def list_packages(device_id: Optional[str] = None) -> Dict:
    """
    List installed packages on a connected Android device using ADB.
    
    Args:
        device_id: Optional device ID for multiple connected devices
    
    Returns:
        Dictionary with list of packages
    """
    command = ["adb"]
    
    if device_id:
        command.extend(["-s", device_id])
    
    command.extend(["shell", "pm", "list", "packages"])
    
    result = run_command(command)
    
    if result["success"]:
        # Parse package list
        packages = []
        for line in result["stdout"].splitlines():
            if line.startswith("package:"):
                packages.append(line[8:])  # Remove "package:" prefix
        
        result["packages"] = packages
        result["count"] = len(packages)
    
    return result


@mcp.tool()
async def analyze_permissions(project_dir: str) -> Dict:
    """
    Analyze permissions declared in AndroidManifest.xml.
    
    Args:
        project_dir: Path to the APKTool project directory
    
    Returns:
        Dictionary with permissions analysis
    """
    manifest_path = os.path.join(project_dir, "AndroidManifest.xml")
    
    if not os.path.exists(manifest_path):
        return {"success": False, "error": f"AndroidManifest.xml not found in {project_dir}"}
    
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_content = f.read()
        
        import re
        
        # Extract permissions
        permission_pattern = r'<uses-permission[^>]*android:name="(.*?)"'
        permissions = re.findall(permission_pattern, manifest_content)
        
        # Extract package name
        package_pattern = r'package="([^"]+)"'
        package_match = re.search(package_pattern, manifest_content)
        package_name = package_match.group(1) if package_match else None
        
        # Extract main activity
        activity_pattern = r'<activity[^>]*android:name="([^"]+)"[^>]*>.*?<action[^>]*android:name="android.intent.action.MAIN".*?<category[^>]*android:name="android.intent.category.LAUNCHER"'
        activity_match = re.search(activity_pattern, manifest_content, re.DOTALL)
        main_activity = activity_match.group(1) if activity_match else None
        
        # Extract min/target SDK version
        min_sdk_pattern = r'<uses-sdk[^>]*android:minSdkVersion="(\d+)"'
        min_sdk_match = re.search(min_sdk_pattern, manifest_content)
        min_sdk = min_sdk_match.group(1) if min_sdk_match else None
        
        target_sdk_pattern = r'<uses-sdk[^>]*android:targetSdkVersion="(\d+)"'
        target_sdk_match = re.search(target_sdk_pattern, manifest_content)
        target_sdk = target_sdk_match.group(1) if target_sdk_match else None
        
        return {
            "success": True,
            "permissions": permissions,
            "permission_count": len(permissions),
            "package_name": package_name,
            "main_activity": main_activity,
            "min_sdk_version": min_sdk,
            "target_sdk_version": target_sdk
        }
    except Exception as e:
        logger.error(f"Error analyzing permissions: {str(e)}")
        return {"success": False, "error": f"Failed to analyze permissions: {str(e)}"}


@mcp.tool()
async def clean_project(project_dir: str, backup: bool = True) -> Dict:
    """
    Clean a project directory to prepare for rebuilding.
    
    Args:
        project_dir: Path to the APKTool project directory
        backup: Whether to create a backup of build directories before cleaning
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        dirs_to_clean = ["build", "dist"]
        cleaned = []
        backed_up = []
        
        for dir_name in dirs_to_clean:
            dir_path = os.path.join(project_dir, dir_name)
            if os.path.exists(dir_path):
                if backup:
                    # Create backup
                    backup_path = f"{dir_path}_backup_{int(time.time())}"
                    shutil.copytree(dir_path, backup_path)
                    backed_up.append({
                        "original": dir_path,
                        "backup": backup_path
                    })
                
                # Remove directory
                shutil.rmtree(dir_path)
                cleaned.append(dir_path)
        
        return {
            "success": True,
            "cleaned_directories": cleaned,
            "backed_up_directories": backed_up
        }
    except Exception as e:
        logger.error(f"Error cleaning project: {str(e)}")
        return {"success": False, "error": f"Failed to clean project: {str(e)}"}


@mcp.tool()
async def create_project(project_name: str, package_name: str) -> Dict:
    """
    Create a new empty APKTool project structure.
    
    Args:
        project_name: Name of the project
        package_name: Java package name (e.g., com.example.app)
    
    Returns:
        Dictionary with operation results
    """
    try:
        # Create project directory in workspace
        project_dir = os.path.join(WORKSPACE_DIR, project_name)
        
        if os.path.exists(project_dir):
            return {"success": False, "error": f"Project directory already exists: {project_dir}"}
        
        # Create directory structure
        os.makedirs(project_dir)
        os.makedirs(os.path.join(project_dir, "res"))
        os.makedirs(os.path.join(project_dir, "smali", *package_name.split(".")))
        os.makedirs(os.path.join(project_dir, "assets"))
        os.makedirs(os.path.join(project_dir, "original", "META-INF"))
        
        # Create basic AndroidManifest.xml
        manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{package_name}"
    android:versionCode="1"
    android:versionName="1.0">

    <uses-sdk
        android:minSdkVersion="21"
        android:targetSdkVersion="33" />

    <application
        android:allowBackup="true"
        android:icon="@drawable/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/AppTheme">
        
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
        
    </application>

</manifest>
"""
        
        # Create basic apktool.yml
        apktool_content = f"""!!brut.androlib.meta.MetaInfo
apkFileName: {project_name}.apk
compressionType: false
doNotCompress:
- resources.arsc
isFrameworkApk: false
packageInfo:
  forcedPackageId: '127'
  renameManifestPackage: null
sdkInfo:
  minSdkVersion: '21'
  targetSdkVersion: '33'
sharedLibrary: false
sparseResources: false
unknownFiles: {{}}
usesFramework:
  ids:
  - 1
  tag: null
version: 2.4.1
versionInfo:
  versionCode: '1'
  versionName: '1.0'
"""
        
        # Write files
        with open(os.path.join(project_dir, "AndroidManifest.xml"), 'w', encoding='utf-8') as f:
            f.write(manifest_content)
        
        with open(os.path.join(project_dir, "apktool.yml"), 'w', encoding='utf-8') as f:
            f.write(apktool_content)
        
        # Create basic resource directories
        res_dirs = ["drawable", "layout", "values", "mipmap"]
        for res_dir in res_dirs:
            os.makedirs(os.path.join(project_dir, "res", res_dir), exist_ok=True)
        
        # Create basic strings.xml
        strings_content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">New App</string>
</resources>
"""
        with open(os.path.join(project_dir, "res", "values", "strings.xml"), 'w', encoding='utf-8') as f:
            f.write(strings_content)
        
        return {
            "success": True,
            "project_dir": project_dir,
            "project_name": project_name,
            "package_name": package_name
        }
    except Exception as e:
        logger.error(f"Error creating project: {str(e)}")
        return {"success": False, "error": f"Failed to create project: {str(e)}"}


@mcp.tool()
async def delete_project(project_dir: str, force: bool = False) -> Dict:
    """
    Delete an APKTool project directory.
    
    Args:
        project_dir: Path to the APKTool project directory
        force: Force deletion without additional checks
    
    Returns:
        Dictionary with operation results
    """
    if not os.path.exists(project_dir):
        return {"success": False, "error": f"Project directory not found: {project_dir}"}
    
    try:
        # Safety check: ensure it's an APKTool project
        if not force and not os.path.exists(os.path.join(project_dir, "apktool.yml")):
            return {
                "success": False,
                "error": "Directory does not appear to be an APKTool project. Use force=True to delete anyway."
            }
        
        # Delete the directory
        shutil.rmtree(project_dir)
        
        return {
            "success": True,
            "message": f"Successfully deleted project directory: {project_dir}"
        }
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        return {"success": False, "error": f"Failed to delete project: {str(e)}"}


@mcp.tool()
async def compare_smali_files(file1_path: str, file2_path: str) -> Dict:
    """
    Compare two smali files and show differences.
    
    Args:
        file1_path: Path to first smali file
        file2_path: Path to second smali file
    
    Returns:
        Dictionary with differences between files
    """
    if not os.path.exists(file1_path):
        return {"success": False, "error": f"First file not found: {file1_path}"}
    
    if not os.path.exists(file2_path):
        return {"success": False, "error": f"Second file not found: {file2_path}"}
    
    try:
        # Read file contents
        with open(file1_path, 'r', encoding='utf-8') as f:
            content1 = f.readlines()
        
        with open(file2_path, 'r', encoding='utf-8') as f:
            content2 = f.readlines()
        
        # Use difflib to find differences
        import difflib
        diff = list(difflib.unified_diff(
            content1, content2, 
            fromfile=os.path.basename(file1_path),
            tofile=os.path.basename(file2_path),
            lineterm=''
        ))
        
        return {
            "success": True,
            "file1": file1_path,
            "file2": file2_path,
            "differences": diff,
            "diff_count": len(diff)
        }
    except Exception as e:
        logger.error(f"Error comparing files: {str(e)}")
        return {"success": False, "error": f"Failed to compare files: {str(e)}"}


@mcp.tool()
async def get_available_devices() -> Dict:
    """
    Get list of available Android devices connected via ADB.
    
    Returns:
        Dictionary with list of devices
    """
    try:
        result = run_command(["adb", "devices", "-l"])
        
        if result["success"]:
            # Parse device list
            devices = []
            lines = result["stdout"].splitlines()
            
            # Skip the first line which is just a header
            for line in lines[1:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        
                        device_info = {
                            "id": device_id,
                            "status": status
                        }
                        
                        # Extract additional properties
                        for part in parts[2:]:
                            if ":" in part:
                                key, value = part.split(":", 1)
                                device_info[key] = value
                        
                        devices.append(device_info)
            
            return {
                "success": True,
                "devices": devices,
                "count": len(devices)
            }
    except Exception as e:
        logger.error(f"Error getting devices: {str(e)}")
        return {"success": False, "error": f"Failed to get devices: {str(e)}"}


if __name__ == "__main__":
    import time  # Import time for backup timestamps
    mcp.run(transport="stdio")