"""
Publication-Quality System Architecture Diagram Generator for AgriRL.

Renders a 300 DPI high-resolution diagram illustrating:
- Branch A: Pest Images -> Preprocessing -> Lightweight CNN -> Softmax Probabilities
- Branch B: agriculture_dataset.csv -> Feature Encoding -> Normalized Sensor Vector
- Fusion: 16-Dimensional Multimodal State S_t
- AgGym Gymnasium Environment & PPO Agent closed-loop sequential transition
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from config import get_default_config

def generate_system_architecture_diagram(save_path: str = None):
    if save_path is None:
        save_path = os.path.join(get_default_config().rl.plots_dir, "system_architecture_diagram.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(15, 8.5), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Background canvas
    bg = patches.Rectangle((0, 0), 100, 100, facecolor="#f8fafc", edgecolor=None)
    ax.add_patch(bg)

    # Title Banner
    ax.text(50, 95.5, "AgriRL: MULTIMODAL VISION-INTEGRATED SYSTEM ARCHITECTURE",
            fontsize=17, fontweight="bold", color="#0f172a", ha="center")
    ax.text(50, 92.5, "Closed-Loop Coupling of Deep Computer Vision and Proximal Policy Optimization (PPO)",
            fontsize=11.5, color="#2d6a4f", ha="center", style="italic")

    def draw_node(x, y, w, h, title, subtitle="", bg="#ffffff", border="#2d6a4f", text_col="#0f172a"):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.0,rounding_size=1.5",
                                     facecolor=bg, edgecolor=border, linewidth=1.8)
        ax.add_patch(box)
        if subtitle:
            ax.text(x + w/2, y + h/2 + 2.0, title, fontsize=10.5, fontweight="bold", color=text_col, ha="center")
            ax.text(x + w/2, y + h/2 - 2.5, subtitle, fontsize=8.2, color="#475569", ha="center")
        else:
            ax.text(x + w/2, y + h/2, title, fontsize=10.5, fontweight="bold", color=text_col, ha="center", va="center")
        return box

    # --- TOP ROW: BRANCH A (COMPUTER VISION) ---
    ax.text(3, 85, "BRANCH A: COMPUTER VISION (PEST PERCEPTION)", fontsize=11, fontweight="bold", color="#1b4332")
    draw_node(3, 70, 16, 11, "Pest Images", "4,187 RGB Files\n(7 Pest Classes)", "#d8f3dc", "#2d6a4f")
    draw_node(24, 70, 16, 11, "Image Preprocessing", "Resize (128x128)\nNorm + Augment", "#ffffff", "#2d6a4f")
    draw_node(45, 70, 17, 11, "Lightweight CNN", "Residual ConvNet\n(1.2M Parameters)", "#d8f3dc", "#1b4332")
    draw_node(67, 70, 17, 11, "Pest Perception Vector", "7-Dim Softmax Prob\nConfidence & ID", "#ffffff", "#2d6a4f")

    # Connect Branch A
    arrow = dict(arrowstyle="-|>", color="#2d6a4f", lw=2.2, mutation_scale=16)
    ax.annotate("", xy=(24, 75.5), xytext=(19, 75.5), arrowprops=arrow)
    ax.annotate("", xy=(45, 75.5), xytext=(40, 75.5), arrowprops=arrow)
    ax.annotate("", xy=(67, 75.5), xytext=(62, 75.5), arrowprops=arrow)

    # --- BOTTOM ROW: BRANCH B (STRUCTURED CROP HEALTH) ---
    ax.text(3, 58, "BRANCH B: STRUCTURED CROP & SENSOR DATA", fontsize=11, fontweight="bold", color="#1e3a8a")
    draw_node(3, 43, 16, 11, "Field Sensor Data", "agriculture_dataset.csv\n(100k+ Records)", "#dbeafe", "#2563eb")
    draw_node(24, 43, 16, 11, "Data Cleaning", "Range Checks &\nOutlier Clamping", "#ffffff", "#2563eb")
    draw_node(45, 43, 17, 11, "Feature Normalization", "Min-Max Scaling [0,1]\nStage & Hotspots", "#dbeafe", "#1e3a8a")
    draw_node(67, 43, 17, 11, "Tabular Sensor Vector", "9-Dim Continuous Obs\n(Temp, Hum, NDVI...)", "#ffffff", "#2563eb")

    # Connect Branch B
    arrow_blue = dict(arrowstyle="-|>", color="#2563eb", lw=2.2, mutation_scale=16)
    ax.annotate("", xy=(24, 48.5), xytext=(19, 48.5), arrowprops=arrow_blue)
    ax.annotate("", xy=(45, 48.5), xytext=(40, 48.5), arrowprops=arrow_blue)
    ax.annotate("", xy=(67, 48.5), xytext=(62, 48.5), arrowprops=arrow_blue)

    # --- MULTIMODAL FUSION NODE ---
    draw_node(87, 53, 11, 23, "Multimodal\nFeature Fusion", "Concatenation\ns_t ∈ [0, 1]¹⁶", "#fef3c7", "#d97706")
    ax.annotate("", xy=(87, 72), xytext=(84, 75.5), arrowprops=dict(arrowstyle="-|>", color="#2d6a4f", lw=2.2, mutation_scale=16))
    ax.annotate("", xy=(87, 58), xytext=(84, 48.5), arrowprops=dict(arrowstyle="-|>", color="#2563eb", lw=2.2, mutation_scale=16))

    # --- REINFORCEMENT LEARNING CORE (LOWER SECTION) ---
    ax.text(3, 33, "REINFORCEMENT LEARNING AGENT & SIMULATED AGRO-ECOSYSTEM", fontsize=11, fontweight="bold", color="#7c2d12")
    fusion_box = patches.Rectangle((3, 5), 94, 25, facecolor="#f1f5f9", edgecolor="#cbd5e1", linewidth=1.5, linestyle="--")
    ax.add_patch(fusion_box)

    draw_node(6, 10, 20, 15, "PPO Policy Network", "Actor-Critic (MlpPolicy)\nClipped Surrogate L_CLIP", "#e2e8f0", "#475569")
    draw_node(33, 10, 19, 15, "Pest-Aware Action", "a ∈ {0, 1, 2, 3}\nNone / Low / Med / High", "#fee2e2", "#dc2626")
    draw_node(59, 10, 22, 15, "AgGym Environment", "Biotic Stress Simulator\nState-Dependent Efficacy", "#ecfdf5", "#059669")
    draw_node(84, 10, 11, 15, "Reward R_t", "Pest & Health Gain\n- Cost - Over-Spray", "#fef3c7", "#d97706")

    # Connect RL Loop
    # Fusion -> PPO
    ax.annotate("", xy=(16, 25), xytext=(92, 53),
                arrowprops=dict(arrowstyle="-|>", color="#d97706", lw=2.5, mutation_scale=18, connectionstyle="arc3,rad=-0.15"))
    ax.text(54, 37, "Unified State Observation Vector  s_t ∈ ℝ¹⁶", color="#b45309", fontsize=9.5, fontweight="bold", ha="center")

    # PPO -> Action
    ax.annotate("", xy=(33, 17.5), xytext=(26, 17.5), arrowprops=dict(arrowstyle="-|>", color="#475569", lw=2.2, mutation_scale=16))
    # Action -> AgGym
    ax.annotate("", xy=(59, 17.5), xytext=(52, 17.5), arrowprops=dict(arrowstyle="-|>", color="#dc2626", lw=2.2, mutation_scale=16))
    # AgGym -> Reward
    ax.annotate("", xy=(84, 17.5), xytext=(81, 17.5), arrowprops=dict(arrowstyle="-|>", color="#059669", lw=2.2, mutation_scale=16))
    # AgGym -> Next State (Feedback loop to PPO)
    ax.annotate("", xy=(16, 10), xytext=(70, 7),
                arrowprops=dict(arrowstyle="-|>", color="#059669", lw=2.2, mutation_scale=16, connectionstyle="arc3,rad=0.22"))
    ax.text(43, 6.2, "Sequential State Transition  s_{t+1}  (25-Week Horizon)", color="#047857", fontsize=9.0, fontweight="bold", ha="center")

    plt.tight_layout()
    fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"[Architecture Generator] Saved System Architecture Diagram to: {save_path}")

if __name__ == "__main__":
    generate_system_architecture_diagram()
