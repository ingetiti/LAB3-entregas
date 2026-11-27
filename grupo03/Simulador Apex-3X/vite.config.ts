import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import fs from 'fs';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    base: './',
    plugins: [
      react(),
      tailwindcss(),
      // Copies src/assets into dist/ so root-relative URLs like
      // "/src/assets/images/..." (e.g. generate_image output) still resolve
      // in production builds. Do not remove.
      {
        name: 'copy-unbundled-src-assets',
        apply: 'build',
        closeBundle(error?: Error): void {
          if (error) {
            return;
          }
          const distDir = path.resolve(__dirname, 'dist');
          const srcAssets = path.resolve(__dirname, 'src/assets');
          const distAssets = path.resolve(distDir, 'src/assets');
          if (fs.existsSync(distDir) && fs.existsSync(srcAssets)) {
            fs.cpSync(srcAssets, distAssets, {recursive: true, force: true});
          }
          const benchSrc = path.resolve(__dirname, 'benchmark');
          const benchDist = path.resolve(distDir, 'benchmark');
          if (fs.existsSync(distDir) && fs.existsSync(benchSrc)) {
            fs.cpSync(benchSrc, benchDist, {recursive: true, force: true});
          }
          for (const file of ['apex3x_assembler.js', 'apex3x_cpu.js', 'apex3x_cli.js', 'app.js']) {
            const srcFile = path.resolve(__dirname, file);
            if (fs.existsSync(distDir) && fs.existsSync(srcFile)) {
              fs.copyFileSync(srcFile, path.resolve(distDir, file));
            }
          }
        },
      },
      {
        name: 'serve-benchmark-dir',
        configureServer(server) {
          server.middlewares.use('/benchmark', (req, res, next) => {
            const cleanPath = (req.url || '/').split('?')[0].replace(/^\/+/, '');
            const target = path.resolve(__dirname, 'benchmark', cleanPath);
            const benchRoot = path.resolve(__dirname, 'benchmark');
            if (!target.startsWith(benchRoot) || !fs.existsSync(target) || fs.statSync(target).isDirectory()) {
              return next();
            }
            res.setHeader('Content-Type', target.endsWith('.json') ? 'application/json; charset=utf-8' : 'text/plain; charset=utf-8');
            fs.createReadStream(target).pipe(res);
          });
        },
      },
    ],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
    },
  };
});
