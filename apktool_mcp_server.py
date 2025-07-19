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
from supabase_integration import init_supabase, log_result
from functools import wraps

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
os.makedirs(WORKSPACE_DIR, exist_ok=True)

# Initialize Supabase client if credentials are provided
init_supabase()


def supabase_logger(func):
    """Decorator to log tool results to Supabase."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        try:
            param_names = func.__code__.co_varnames[:func.__code__.co_argcount]
            params = {name: val for name, val in zip(param_names, args)}
            params.update(kwargs)
            log_result(func.__name__, params, result)
        except Exception as e:
            logger.error(f"Supabase logging error for {func.__name__}: {e}")
        return result

    return wrapper



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
@supabase_logger
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
        return {
            "success": True,
            "output_dir": output_dir
        }
    else:
        return result

@mcp.tool(name="build_apk", description="Build an APK file from a decoded APKTool project.")
@supabase_logger
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
        return {
            "success": False, 
            "error": f"Project directory not found: {project_dir}"
        }
    
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
@supabase_logger
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
        return {
            "success": False, 
            "error": f"AndroidManifest.xml not found in {project_dir}"
        }

    try:
        with open(manifest_path, 'r', encoding="utf-8") as f:
            content = f.read()
        return {
            "success": True, 
            "manifest": content, 
            "path": manifest_path
        }
    except Exception as e:
        logger.error(f"Error reading manifest: {str(e)}")
        return {
            "success": False, 
            "error": f"Failed to read AndroidManifest.xml: {str(e)}"
        }

@mcp.tool(name="get_apktool_yml", description="Get apktool.yml information from a decoded APK project.")
@supabase_logger
async def get_apktool_yml(project_dir: str) -> Dict:
    """
    Get apktool.yml information from a decoded APK project.

    Args:
        project_dir: Path to APKTool project directory

    Returns:
        Dictionary with apktool.yml content or error
    """

    yml_path = os.path.join(project_dir, "apktool.yml")

    if not os.path.exists(yml_path):
        return {
            "success": False, 
            "error": f"apktool.yml not found in {project_dir}"
        }

    try:
        with open(yml_path, 'r', encoding="utf-8") as f:
            content = f.read()
        return {
            "success": True,
            "content": content,
            "path": yml_path
        }
    except Exception as e:
        logger.error(f"Error reading apktool.yml: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to read apktool.yml: {str(e)}"
        }

@mcp.tool(name="list_smali_directories", description="List all smali directories in a project")
@supabase_logger
async def list_smali_directories(project_dir: str) -> Dict:
    """
    List all smali directories in a project.

    Args:
        project_dir: Path to the APKTool project directory

    Returns:
        Dictionary with list of smali directories
    """

    if not os.path.exists(project_dir):
        return {
            "success": False,
            "error": f"Project directory not found: {project_dir}"
        }
    
    try:
        smali_dirs = [d for d in os.listdir(project_dir) 
                      if d.startswith("smali") 
                      and os.path.isdir(os.path.join(project_dir, d))]
        
        return {
            "success": True,
            "smali_dirs": smali_dirs,
            "count": len(smali_dirs)
        }
    except Exception as e:
        logger.error(f"Error listing smali directories: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list smali directories: {str(e)}"
        }

@mcp.tool(name="list_smali_files", description="List smali files in a specific smali directory, optionally filtered by package prefix.")
@supabase_logger
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
                     if d.startswith("smali") 
                     and os.path.isdir(os.path.join(project_dir, d))]
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
        logger.error(F"Error listing smali files: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to list smali files: {str(e)}"
        }

@mcp.tool(name="get_smali_file", description="Get content of a specific smali file by class name.")
@supabase_logger
async def get_smali_file(project_dir: str, class_name: str) -> Dict:
    """
    Get content of a specific smali file by class name.

    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)

    Returns:
        Dictionary with smali file content.
    """

    if not os.path.exists(project_dir):
        return {
            "success": False,
            "error": f"Project directory not found: {project_dir}"
        }
    
    try:
        # Look for the class in all smali directories
        smali_dirs = [d for d in os.listdir(project_dir)
                      if d.startswith("smali")
                      and os.path.isdir(os.path.join(project_dir, d))]

        for smali_dir in smali_dirs:
            file_path = os.path.join(
                project_dir, 
                smali_dir, 
                class_name.replace('.', os.path.sep) + '.smali'
            )

            if os.path.exists(file_path):
                with open(file_path, 'r', encoding="utf-8") as f:
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
        return {
            "success": False,
            "error": f"Failed to get smali file: {str(e)}"
        }

@mcp.tool(name="modify_smali_file", description="Modify the content of a specific smali file.")
@supabase_logger
async def modify_smali_file(project_dir: str, class_name: str, new_content: str, create_backup: bool = True) -> Dict:
    """
    Modify the content of a specific smali file.

    Args:
        project_dir: Path to the APKTool project directory
        class_name: Full class name (e.g., com.example.MyClass)
        new_content: New content for the smali file
        create_backup: Whether to create a backup of the original file

    Returns:
        Dictionary with operation results.
    """

    if not os.path.exists(project_dir):
        return {
            "success": False, 
            "error": f"Project directory not found: {project_dir}"
        }
    
    try:
        # Look for the class in all smali directories
        smali_dirs = [d for d in os.listdir(project_dir)
                      if d.startswith("smali")
                      and os.path.isdir(os.path.join(project_dir, d))]

        file_path = None
        for smali_dir in smali_dirs:
            test_path = os.path.join(
                project_dir,
                smali_dir,
                class_name.replace('.', os.path.sep) + '.smali'
                )
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
        return {
            "success": False,
            "error": f"Failed to modify smali file: {str(e)}"
        }

@mcp.tool(name="list_resources", description="List resources in a project, optionally filtered by resource type.")
@supabase_logger
async def list_resources(project_dir: str, resource_type: Optional[str] = None) -> Dict:
    """
    List resources in a project, optionally filtered by resource type.

    Args:
        project_dir: Path to the APKTool project directory
        resource_type: Optional resource type to the filter by (e.g., "layout", "drawable")

    Returns:
        Dictionary with list of resources
    """

    res_path = os.path.join(project_dir, "res")

    if not os.path.exists(res_path):
        return {
            "success": False,
            "error": f"Resources directory not found: {res_path}"
        }

    try: 
        if resource_type:
            # List resources of specific type
            type_path = os.path.join(res_path, resource_type)
            if not os.path.exists(type_path):
                resource_types = [
                    d for d in os.listdir(res_path) 
                    if os.path.isdir(os.path.join(res_path, d))
                ]
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
                    resource_count = len([
                        f for f in os.listdir(type_path) 
                        if os.path.isfile(os.path.join(type_path, f))
                    ])
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
        return {
            "success": False,
            "error": f"Failed to list resources: {str(e)}"
        }
    
@mcp.tool(name="get_resource_file", description="Get content of a specific resource file.")
@supabase_logger
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
        return {
            "success": False,
            "error": f"Resource file not found: {resource_path}"
        }
    
    try:
        with open(resource_path, 'r', encoding="utf-8") as f:
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
        return {
            "success": False,
            "error": f"Failed to get resource file: {str(e)}"
        }

@mcp.tool(name="modify_resource_file", description="Modify the content of a specific resource file.")
@supabase_logger
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
        Dictionary with operation results.
    """

    resource_path = os.path.join(project_dir, "res", resource_type, resource_name)

    if not os.path.exists(resource_path):
        return {
            "success": False,
            "error": f"Resource file not found: {resource_path}"
        }

    try:
        # create backup if requested
        backup_path = None
        if create_backup:
            backup_path = resource_path + ".bak"
            shutil.copy2(resource_path, backup_path)
        
        # write new content
        with open(resource_path, 'w', encoding="utf-8") as f:
            f.write(new_content)
        
        return {
            "success": True,
            "message": f"Successfully modified {resource_path}",
            "path": resource_path,
            "backup_path": backup_path
        }
    except Exception as e:
        logger.error(f"Error modifying resource file: {str(e)}")
        return {
            "success": False,
            "error": f"Failed to modify resource file: {str(e)}"
        }
    
@mcp.tool(name="search_in_files", description="Search for a pattern in files specified extensions.")
@supabase_logger
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
        return {
            "success": False,
            "error": f"Project directory not found: {project_dir}"
        }
    
    try:
        results = []

        for root, _, files in os.walk(project_dir):
            for file in files:
                if len(results) >= max_results:
                    break

                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding="utf-8") as f:
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
        return {
            "success": False,
            "error": f"Failed to search in files: {str(e)}"
        }

@mcp.tool(name="clean_project", description="Clean a project directory to prepare for rebuilding.")
@supabase_logger
async def clean_project(project_dir: str, backup: bool = True) -> Dict:
    """
    Clean a project directory to prepare for rebuilding.
    
    Args:
        project_dir: Path to the APKTool project directory
        backup: Whether to create a backup of build directories before cleaning
    
    Returns:
        Dictionary with operation results
    """
    import time
    if not os.path.exists(project_dir):
        return {
            "success": False,
            "error": f"Project directory not found: {project_dir}"
        }
    
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
        return {
            "success": False,
            "error": f"Failed to clean project: {str(e)}"
        }

if __name__ == "__main__":
    mcp.run(transport="stdio")
