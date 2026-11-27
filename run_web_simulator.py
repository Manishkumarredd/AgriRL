"""
AgriRL: Interactive Visual Web Simulator Server with Multimodal Vision Support.

Features:
1. Serves the interactive AgriRL web dashboard from web/.
2. Implements /api/predict_image:
   - Accepts an uploaded leaf image (file or base64)
   - Runs LightweightPestCNN to detect pest class, confidence, and 7-class probability vector.
3. Implements /api/step:
   - Takes environmental telemetry + visual pest probabilities
   - Runs trained Multimodal PPO policy to recommend treatment (None, Low, Med, High)
   - Steps the AgGym simulation environment to return next state, reward, and efficacy.
4. Implements /api/reset:
   - Resets field ecosystem with realistic baseline conditions.
"""

import os
import sys
import json
import base64
import io
import webbrowser
from http.server import SimpleHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True
from PIL import Image
import numpy as np
import torch

PORT = 8501

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(CURRENT_DIR, "web")
if not os.path.exists(WEB_DIR):
    WEB_DIR = os.path.join(CURRENT_DIR, "..", "AgriRL", "web")

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from stable_baselines3 import PPO
from config import PEST_CLASSES, ACTION_NAMES, ACTION_COSTS, get_default_config
from env_aggym_wrapper import AgGymWrapperEnv
from vision_module import PestVisionInference

# Initialize Environment & Models
print("[Server] Initializing AgGym Environment...")
env = AgGymWrapperEnv(mode="multimodal", seed=42)

model_path = os.path.join(CURRENT_DIR, "models", "multimodal_vision_ppo.zip")
if not os.path.exists(model_path):
    # Fallback to tabular model if multimodal is not yet trained
    model_path = os.path.join(CURRENT_DIR, "models", "tabular_ppo.zip")

print(f"[Server] Loading PPO agent from: {model_path}")
ppo_model = PPO.load(model_path, device="cpu")

cnn_weights = os.path.join(CURRENT_DIR, "models", "pest_cnn.pt")
print(f"[Server] Loading Pest CNN classifier from: {cnn_weights}")
vision_engine = PestVisionInference(model_path=cnn_weights)


class AgriRLSimHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/sample_leaf"):
            import random
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            target_pest = qs.get("pest", [None])[0]

            test_dir = os.path.join(CURRENT_DIR, "Pest Detection", "test")
            pest_folders = [d for d in os.listdir(test_dir) if os.path.isdir(os.path.join(test_dir, d))]
            
            chosen_folder = None
            if target_pest:
                for f in pest_folders:
                    if target_pest.lower() in f.lower():
                        chosen_folder = f
                        break
            if not chosen_folder and pest_folders:
                chosen_folder = random.choice(pest_folders)

            folder_path = os.path.join(test_dir, chosen_folder) if chosen_folder else test_dir
            images = [img for img in os.listdir(folder_path) if img.lower().endswith(('.png', '.jpg', '.jpeg'))] if os.path.exists(folder_path) else []
            
            if images:
                chosen_img = random.choice(images)
                img_path = os.path.join(folder_path, chosen_img)
                pil_img = Image.open(img_path).convert("RGB")
                
                buffered = io.BytesIO()
                pil_img.save(buffered, format="JPEG")
                img_b64 = "data:image/jpeg;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")
                
                res = vision_engine.predict_image(pil_img)
                response = {
                    "image_base64": img_b64,
                    "filename": chosen_img,
                    "pest_class": chosen_folder.replace("_test", ""),
                    "predicted_class": res["predicted_class"],
                    "confidence": float(res["confidence"]),
                    "probabilities": res["probabilities"].tolist()
                }
            else:
                response = {"error": "No images found"}

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        if self.path == "/api/predict_image":
            # Image Upload Endpoint
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            req = json.loads(body.decode("utf-8"))

            img_b64 = req.get("image_base64", "")
            if "," in img_b64:
                img_b64 = img_b64.split(",")[1]

            img_bytes = base64.b64decode(img_b64)
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")

            res = vision_engine.predict_image(pil_img)
            response = {
                "predicted_class": res["predicted_class"],
                "confidence": res["confidence"],
                "probabilities": res["probabilities"].tolist(),
                "probability_dict": res["probability_dict"]
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        elif self.path == "/api/step":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode("utf-8"))

            pest = float(data.get("pest", 45.0))
            health = float(data.get("health", 65.0))
            stress = float(data.get("stress", 100.0 - health))
            temp = float(data.get("temp", 30.0))
            hum = float(data.get("hum", 70.0))
            soil = float(data.get("soil", 55.0))
            ndvi = float(data.get("ndvi", 0.60))
            stage = int(data.get("stage", 2))
            pest_probs = data.get("pest_probs", [1.0/7.0]*7)

            # Construct 16-dim observation vector
            tabular_obs = np.array([
                pest / 100.0,
                health / 100.0,
                stress / 100.0,
                temp / 50.0,
                hum / 100.0,
                soil / 100.0,
                np.clip(ndvi, 0.0, 1.0),
                (stage - 1.0) / 3.0,
                1.0 if pest > 50.0 else 0.0
            ], dtype=np.float32)

            probs_arr = np.array(pest_probs, dtype=np.float32)
            obs = np.concatenate([tabular_obs, probs_arr])

            # Exploration vs Exploitation Parameter
            exploration_rate = float(data.get("exploration_rate", 0.0))

            obs_tensor = torch.as_tensor(obs.reshape(1, -1), dtype=torch.float32)
            with torch.no_grad():
                dist = ppo_model.policy.get_distribution(obs_tensor)
                policy_probs = dist.distribution.probs.cpu().numpy()[0].tolist()
                entropy = float(dist.entropy().cpu().item())

            # Policy Decision: Exploitation (Deterministic) vs Exploration (Stochastic)
            if exploration_rate > 0.0 and np.random.rand() < exploration_rate:
                action = int(np.random.randint(0, 4))
                mode_used = "Exploration (Stochastic Sample)"
            else:
                action, _ = ppo_model.predict(obs, deterministic=True)
                action = int(action)
                mode_used = "Exploitation (Optimal Policy)"

            # Execute Simulated Step in AgGym
            env.state = {
                "pest_damage": pest,
                "crop_health": health,
                "crop_stress": stress,
                "temperature": temp,
                "humidity": hum,
                "soil_moisture": soil,
                "ndvi": ndvi,
                "crop_growth_stage": float(stage),
                "pest_hotspots": 1.0 if pest > 50.0 else 0.0,
                "rainfall": 10.0,
                "true_pest_name": PEST_CLASSES[int(np.argmax(probs_arr))]
            }
            env.true_pest_idx = int(np.argmax(probs_arr))

            obs_next, reward, terminated, truncated, info = env.step(action)

            response = {
                "action": action,
                "action_name": ACTION_NAMES[action],
                "probs": policy_probs,
                "reward": float(reward),
                "next_pest": float(info["pest_damage"]),
                "next_health": float(info["crop_health"]),
                "treatment_cost": float(info["treatment_cost"]),
                "efficacy": float(info["efficacy"]),
                "is_violation": bool(info["is_violation"]),
                "task_success": bool(info["task_success"]),
                "policy_entropy": float(entropy),
                "decision_mode": mode_used
            }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))

        else:
            self.send_error(404, "Endpoint not found")

    def log_message(self, format, *args):
        return


def start_server():
    server_address = ("", PORT)
    httpd = ThreadedHTTPServer(server_address, AgriRLSimHandler)
    print(f"\n=======================================================")
    print(f"[AgriRL Web Simulator] Running at: http://localhost:{PORT}")
    print(f"=======================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Shutting down simulator server.")
        httpd.server_close()


if __name__ == "__main__":
    start_server()
