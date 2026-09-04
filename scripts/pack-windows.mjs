import { execSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const stage = path.join(root, "release", "kaipanla");
const zipPath = path.join(root, "deploy", "kaipanla-windows.zip");
const artifactZip = "/opt/cursor/artifacts/kaipanla-windows.zip";

function rm(p) {
  fs.rmSync(p, { recursive: true, force: true });
}

function copyFile(from, to) {
  fs.mkdirSync(path.dirname(to), { recursive: true });
  fs.copyFileSync(from, to);
}

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    const src = path.join(from, entry.name);
    const dest = path.join(to, entry.name);
    if (entry.isDirectory()) copyDir(src, dest);
    else copyFile(src, dest);
  }
}

execSync("npm run build", { cwd: root, stdio: "inherit" });

rm(stage);
fs.mkdirSync(stage, { recursive: true });
fs.mkdirSync(path.join(root, "deploy"), { recursive: true });

copyDir(path.join(root, "dist"), path.join(stage, "dist"));
copyFile(path.join(root, "server", "index.mjs"), path.join(stage, "server", "index.mjs"));
copyFile(path.join(root, "server", "tdx.mjs"), path.join(stage, "server", "tdx.mjs"));
copyFile(path.join(root, "server", "tdx_bridge.py"), path.join(stage, "server", "tdx_bridge.py"));
copyFile(path.join(root, "requirements-tdx.txt"), path.join(stage, "requirements-tdx.txt"));
copyFile(path.join(root, "stop.bat"), path.join(stage, "stop.bat"));

fs.writeFileSync(
  path.join(stage, "package.json"),
  `${JSON.stringify(
    {
      name: "kaipanla-ui",
      private: true,
      version: "1.0.0",
      type: "module",
      scripts: { start: "node server/index.mjs" },
      dependencies: { express: "^4.21.2" },
    },
    null,
    2,
  )}\n`,
);

fs.writeFileSync(
  path.join(stage, "start.bat"),
  `@echo off
setlocal
cd /d "%~dp0"
title KaiPanLa

where node >nul 2>&1
if errorlevel 1 (
  echo [ERROR] Please install Node.js 18+ first.
  echo https://nodejs.org/
  start https://nodejs.org/
  pause
  exit /b 1
)

if not exist "node_modules\\" (
  echo Installing express...
  call npm install --omit=dev
  if errorlevel 1 (
    echo npm install failed. Check your network.
    pause
    exit /b 1
  )
)

where python >nul 2>&1
if not errorlevel 1 (
  if not exist "%LOCALAPPDATA%\\kaipanla-tdx.flag" (
    echo Installing eltdx for stock charts...
    python -m pip install -r requirements-tdx.txt
    if not errorlevel 1 (
      echo ok> "%LOCALAPPDATA%\\kaipanla-tdx.flag"
    )
  )
  start "KaiPanLa-TDX" /min cmd /c "python -m eltdx.http_server --host 127.0.0.1 --port 8790 --tdx-host 115.238.90.165:7709 --log-level warning"
) else (
  echo [WARN] Python not found. Auction list works, but stock 分时/日K charts need Python + eltdx.
)

set NODE_ENV=production
set PORT=3000
set HOST=127.0.0.1
set TDX_HTTP_URL=http://127.0.0.1:8790
echo.
echo KaiPanLa: http://127.0.0.1:3000
echo Close this window to stop.
echo.
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:3000"
node server\\index.mjs
if errorlevel 1 pause
`,
);

fs.writeFileSync(
  path.join(stage, "使用说明.txt"),
  `开盘啦 · 市场雷达  （解压即用）

1. 安装 Node.js 18 或更高：https://nodejs.org/  （勾选加入 PATH）
2. 把本文件夹整个放到 F 盘，例如：
     F:\\kaipanla
   解压后应能看到 start.bat、dist、server 这三个。
3. 双击 start.bat
4. 浏览器会打开 http://127.0.0.1:3000
   关掉那个黑色窗口即停止服务；或双击 stop.bat

首次若没有 node_modules，start.bat 会自动 npm install，需要能上网。
`,
);

execSync("npm install --omit=dev", { cwd: stage, stdio: "inherit" });

rm(zipPath);
execSync(`zip -r -q "${zipPath}" kaipanla`, {
  cwd: path.join(root, "release"),
  stdio: "inherit",
});

fs.mkdirSync(path.dirname(artifactZip), { recursive: true });
fs.copyFileSync(zipPath, artifactZip);

const stat = fs.statSync(zipPath);
console.log(`packed ${zipPath} (${Math.round(stat.size / 1024)} KB)`);
console.log(`copied ${artifactZip}`);
