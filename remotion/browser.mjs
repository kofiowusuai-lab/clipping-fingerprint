import {access,stat} from 'node:fs/promises';
import {constants} from 'node:fs';
import path from 'node:path';
import os from 'node:os';

/** Resolve an installed browser only; never download Chrome or use cloud rendering. */
export async function findBrowser(env = process.env, platform = process.platform) {
  const executable = async (file) => {
    try { await access(file, constants.X_OK); return (await stat(file)).isFile(); } catch { return false; }
  };
  if (env.REMOTION_BROWSER_EXECUTABLE) {
    const explicit = path.resolve(env.REMOTION_BROWSER_EXECUTABLE);
    if (!await executable(explicit)) throw new Error('REMOTION_BROWSER_EXECUTABLE is not an executable local file');
    return explicit;
  }
  const candidates = platform === 'darwin' ? [
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    path.join(os.homedir(), 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
    '/Applications/Chromium.app/Contents/MacOS/Chromium',
  ] : platform === 'win32' ? [
    ...['PROGRAMFILES', 'PROGRAMFILES(X86)', 'LOCALAPPDATA'].filter(k => env[k]).map(k => path.join(env[k], 'Google/Chrome/Application/chrome.exe')),
  ] : ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome', '/opt/google/chrome/chrome'];
  for (const dir of (env.PATH ?? '').split(path.delimiter)) {
    for (const name of platform === 'win32' ? ['chrome.exe', 'chromium.exe'] : ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']) {
      if (dir) candidates.push(path.join(dir, name));
    }
  }
  for (const file of candidates) if (await executable(file)) return file;
  throw new Error('No installed Chrome/Chromium found. Set REMOTION_BROWSER_EXECUTABLE; automatic browser downloads are disabled.');
}
