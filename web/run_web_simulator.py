"""
AgriRL Web Simulator Launcher (web/ folder)
"""
import os
import sys

agrirl_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
script = os.path.join(agrirl_dir, "run_web_simulator.py")

if __name__ == "__main__":
    os.chdir(agrirl_dir)
    with open(script, "r", encoding="utf-8") as f:
        code = compile(f.read(), script, "exec")
        exec(code, {"__file__": script, "__name__": "__main__"})
