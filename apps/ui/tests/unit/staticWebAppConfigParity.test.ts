import fs from 'node:fs';
import path from 'node:path';

describe('staticwebapp config parity', () => {
  it('keeps root and public staticwebapp.config.json in sync', () => {
    const rootConfigPath = path.join(process.cwd(), 'staticwebapp.config.json');
    const publicConfigPath = path.join(process.cwd(), 'public', 'staticwebapp.config.json');

    const rootConfig = JSON.parse(fs.readFileSync(rootConfigPath, 'utf8'));
    const publicConfig = JSON.parse(fs.readFileSync(publicConfigPath, 'utf8'));

    expect(publicConfig).toEqual(rootConfig);
  });
});
