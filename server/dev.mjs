import { spawn } from "node:child_process";

const children = [];

function run(command, args, extraEnv = {}) {
  const child = spawn(command, args, {
    stdio: "inherit",
    env: { ...process.env, ...extraEnv },
  });
  children.push(child);
  child.on("exit", (code) => {
    if (shuttingDown) return;
    shuttingDown = true;
    for (const other of children) {
      if (other !== child) other.kill("SIGTERM");
    }
    process.exit(code ?? 1);
  });
}

let shuttingDown = false;
function shutdown() {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children) child.kill("SIGTERM");
  process.exit(0);
}

process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);

run("node", ["server/index.mjs"], { PORT: "8787", NODE_ENV: "development" });
run("npx", ["vite", "--host", "0.0.0.0", "--port", "5173"]);
