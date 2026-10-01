import { writeFileSync } from 'node:fs';

// This origin is public browser configuration. Never place backend credentials here.
const origin = (process.env.CORNERSCOUT_API_BASE_URL ?? '').trim().replace(/\/$/, '');
if (process.env.VERCEL && !origin && process.env.CORNERSCOUT_SAME_ORIGIN !== '1') {
  throw new Error('Configure CORNERSCOUT_API_BASE_URL with the public HTTPS backend origin before deploying.');
}
if (origin) {
  const url = new URL(origin);
  const local = ['localhost', '127.0.0.1'].includes(url.hostname);
  if ((!local && url.protocol !== 'https:') || !['http:', 'https:'].includes(url.protocol)
      || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('CORNERSCOUT_API_BASE_URL must be a public HTTPS origin without paths or credentials.');
  }
}
writeFileSync(new URL('../public/config.json', import.meta.url), JSON.stringify({apiBaseUrl:origin})+'\n');
