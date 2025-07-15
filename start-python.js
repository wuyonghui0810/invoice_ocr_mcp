  // start-python.js
  const { spawn } = require('child_process');
  const proc = spawn('python', ['main.py'], { stdio: 'inherit' });
  proc.on('close', code => process.exit(code));