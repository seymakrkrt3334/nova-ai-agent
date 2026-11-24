const { app, BrowserWindow } = require("electron");
const fs = require("fs");
const http = require("http");
const path = require("path");

const dist = path.resolve(__dirname, "..", "dist");
const port = 4173;

function contentType(file) {
  const types = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
  };
  return types[path.extname(file).toLowerCase()] || "application/octet-stream";
}

function insideDist(file) {
  const root = dist.endsWith(path.sep) ? dist : `${dist}${path.sep}`;
  return file === dist || file.startsWith(root);
}

function startStatic() {
  const server = http.createServer((request, response) => {
    let pathname = "/";
    try {
      pathname = decodeURIComponent(new URL(request.url || "/", "http://127.0.0.1").pathname);
    } catch {
      pathname = "/";
    }
    const requested = path.resolve(dist, `.${pathname}`);
    const file = insideDist(requested) && fs.existsSync(requested) && fs.statSync(requested).isFile()
      ? requested
      : path.join(dist, "index.html");
    fs.readFile(file, (error, data) => {
      if (error) {
        response.writeHead(404);
        response.end();
        return;
      }
      response.writeHead(200, { "Content-Type": contentType(file) });
      response.end(data);
    });
  });
  server.listen(port, "127.0.0.1");
  return server;
}

function createWindow() {
  const window = new BrowserWindow({
    width: 1200,
    height: 800,
    title: "NOVA AI",
    autoHideMenuBar: true,
    backgroundColor: "#07060d",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  window.loadURL(`http://127.0.0.1:${port}`);
}

app.whenReady().then(() => {
  const server = startStatic();
  server.once("listening", createWindow);
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
