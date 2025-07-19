import { useState } from 'react';

export default function App() {
  const [apkPath, setApkPath] = useState('');
  const [output, setOutput] = useState('');

  const decodeApk = async () => {
    const res = await fetch('/api/decode_apk', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ apk_path: apkPath })
    });
    const data = await res.json();
    setOutput(JSON.stringify(data, null, 2));
  };

  return (
    <div style={{ padding: '1rem' }}>
      <h1>APKTool MCP UI</h1>
      <div>
        <input
          type="text"
          placeholder="Path to APK"
          value={apkPath}
          onChange={(e) => setApkPath(e.target.value)}
        />
        <button onClick={decodeApk}>Decode APK</button>
      </div>
      <pre>{output}</pre>
    </div>
  );
}
