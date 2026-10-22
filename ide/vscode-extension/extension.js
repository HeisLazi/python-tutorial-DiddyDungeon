const vscode = require('vscode');

let panel;

function openDashboard() {
  if (panel) {
    panel.reveal(vscode.ViewColumn.Beside);
    return;
  }
  panel = vscode.window.createWebviewPanel(
    'questlabDashboard',
    'Quest Lab Dashboard',
    vscode.ViewColumn.Beside,
    { enableScripts: true }
  );
  panel.webview.html = getHtml();
  panel.onDidDispose(() => { panel = undefined; });
}

function getHtml() {
  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Quest Lab</title></head>
<body style="margin:0;padding:0;background:#1e1e1e;color:#d4d4d4;font-family:sans-serif;">
  <div style="padding:16px;">
    <h2>Quest Lab Dashboard</h2>
    <p>Start the backend first, then open the dashboard.</p>
    <iframe src="http://localhost:5173" style="width:100%;height:80vh;border:1px solid #333;"></iframe>
  </div>
</body>
</html>`;
}

function startBackend() {
  const terminal = vscode.window.createTerminal('Quest Lab Backend');
  terminal.show();
  terminal.sendText('cd /home/lazi/projects/python-tutorial-DiddyDungeon && diddy-dungeon --no-browser');
}

function activate(context) {
  context.subscriptions.push(
    vscode.commands.registerCommand('questlab.openDashboard', openDashboard),
    vscode.commands.registerCommand('questlab.startBackend', startBackend)
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
