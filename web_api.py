from fastapi import FastAPI
import uvicorn
import apktool_mcp_server as server

app = FastAPI(title="APKTool MCP API")

@app.post("/decode_apk")
async def decode_apk(apk_path: str, force: bool = True, no_res: bool = False, no_src: bool = False):
    return await server.decode_apk(apk_path, force, no_res, no_src)

@app.post("/build_apk")
async def build_apk(project_dir: str, output_apk: str | None = None, debug: bool = True, force_all: bool = False):
    return await server.build_apk(project_dir, output_apk, debug, force_all)

@app.post("/get_manifest")
async def get_manifest(project_dir: str):
    return await server.get_manifest(project_dir)


if __name__ == "__main__":
    uvicorn.run("web_api:app", host="0.0.0.0", port=8000)
