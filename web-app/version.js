const fs = require('fs');
const execSync = require('child_process').execSync;

// Get the latest git commit hash
const gitCommit = execSync('git rev-parse --short HEAD').toString().trim();

// The path to the file we will create/overwrite
const targetPath = './src/environments/version.ts';

const content = `export const VERSION = {
  commit: '${gitCommit}',
  buildDate: '${new Date().toISOString()}'
};
`;

fs.writeFileSync(targetPath, content);
console.log(`Version file generated with commit: ${gitCommit}`);
