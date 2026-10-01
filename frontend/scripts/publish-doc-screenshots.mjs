import { copyFileSync, existsSync, mkdirSync } from 'node:fs';

// These are screenshots produced by the real historical E2E journey.
const destination = new URL('../../docs/images/', import.meta.url);
const screenshots = [
  ['summary-visual-desktop.png', 'summary.png'],
  ['map-heat-desktop.png', 'map.png'],
];
for (const [source] of screenshots) {
  if (!existsSync(new URL(`../test-results/${source}`, import.meta.url))) {
    throw new Error(`Missing ${source}; run the frontend E2E suite first.`);
  }
}
mkdirSync(destination, { recursive: true });
for (const [source, target] of screenshots) {
  copyFileSync(new URL(`../test-results/${source}`, import.meta.url), new URL(target, destination));
}
console.log('Published historical E2E screenshots to docs/images.');
