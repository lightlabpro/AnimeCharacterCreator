"""Browser end-to-end: real app, real import button, generated pack. Skipped when Chromium or Playwright are not installed."""
import os, pathlib, shutil, socket, subprocess, sys, time, unittest, urllib.request

root = pathlib.Path(__file__).resolve().parents[2]
CHROMIUM = os.environ.get("CHROMIUM_PATH", "/opt/pw-browsers/chromium")
PLAYWRIGHT = os.environ.get("PLAYWRIGHT_PATH", "/opt/node-tools/node_modules/playwright")

@unittest.skipUnless(os.path.exists(CHROMIUM) and os.path.exists(PLAYWRIGHT) and shutil.which("node") and (root / "node_modules").exists(), "needs Chromium, Playwright and npm install")
class PackEndToEnd(unittest.TestCase):
    def test_import_slider_performance_and_socket_attachment(self):
        with socket.socket() as s: s.bind(("127.0.0.1", 0)); port = s.getsockname()[1]
        vite = subprocess.Popen(["npx", "vite", "--port", str(port), "--strictPort"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(60):
                try: urllib.request.urlopen(f"http://localhost:{port}", timeout=1); break
                except Exception: time.sleep(0.5)
            r = subprocess.run(["node", "scripts/e2e_pack.cjs", "--url", f"http://localhost:{port}"], cwd=root, capture_output=True, text=True, timeout=240)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("E2E OK", r.stdout); self.assertIn("SOC-HeadTop", r.stdout)
        finally:
            vite.terminate()

if __name__ == "__main__":
    unittest.main()
