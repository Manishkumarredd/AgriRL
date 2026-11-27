"""
Academic State-Action-Reward Poster Generator for AgriRL.

Generates a publication-grade, high-resolution infographic poster (300 DPI)
illustrating the closed-loop MDP formulation:
State -> PPO Agent -> Action -> Agricultural Environment -> Reward -> Updated State.
"""

import os
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from config import get_default_config

def generate_state_action_reward_poster(save_path: str = None):
    if save_path is None:
        save_path = os.path.join(get_default_config().rl.plots_dir, "state_action_reward_poster.png")
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 8), dpi=300)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    # Background canvas
    bg = patches.Rectangle((0, 0), 100, 100, facecolor="#0b1712", edgecolor=None)
    ax.add_patch(bg)

    # Title Banner
    ax.text(50, 94.5, "AgriRL: CLOSED-LOOP STATE-ACTION-REWARD MDP FORMULATION",
            fontsize=18, fontweight="bold", color="#ffffff", ha="center")
    ax.text(50, 91.0, "Multimodal Vision-Integrated Reinforcement Learning for Adaptive Precision Pest Management",
            fontsize=12, color="#52b788", ha="center", style="italic")

    # Helper function for glowing cards
    def draw_card(x, y, w, h, title, bg_col="#132a1e", border_col="#52b788"):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=1.2,rounding_size=2.0",
                                     facecolor=bg_col, edgecolor=border_col, linewidth=2.0)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 4.5, title, fontsize=12, fontweight="bold", color="#ffffff", ha="center")
        return box

    # 1. STATE BOX (Left)
    draw_card(4, 30, 26, 54, "STATE SPACE  S ∈ [0, 1]¹⁶", "#102619", "#2d6a4f")
    state_text = (
        "Branch A: Vision Perception (CNN)\n"
        " • Aphid Probability (p₁)\n"
        " • Armyworm Probability (p₂)\n"
        " • Beetle Probability (p₃)\n"
        " • Mite Probability (p₄)\n"
        " • Sawfly Probability (p₅)\n"
        " • Stem Borer Probability (p₆)\n"
        " • Stem Fly Probability (p₇)\n"
        " • Classification Confidence\n\n"
        "Branch B: Agro-Climatic Sensors\n"
        " • Pest Damage Severity (%)\n"
        " • Crop Health Index (%)\n"
        " • Crop Stress Indicator (%)\n"
        " • Canopy NDVI Score\n"
        " • Ambient Temperature (°C)\n"
        " • Relative Humidity (%)\n"
        " • Soil Moisture Volume (%)\n"
        " • Crop Phenological Stage (1-4)\n"
        " • Spatial Pest Hotspot Flag"
    )
    ax.text(6.5, 75, state_text, fontsize=9.2, color="#d8f3dc", va="top", family="sans-serif", linespacing=1.35)

    # 2. PPO AGENT (Center-Left)
    draw_card(36, 52, 28, 32, "PPO DECISION AGENT", "#1a2c3a", "#2563eb")
    agent_text = (
        "Actor-Critic Neural Policy π_θ(a|s)\n"
        "------------------------------------\n"
        " • Clipped Surrogate Objective:\n"
        "   L_CLIP(θ) = E [ min(r_t Â_t, clip·Â_t) ]\n"
        " • Value Function Baseline V_φ(s)\n"
        " • Generalized Advantage Estimation (GAE)\n"
        " • Maximum Entropy Exploration:\n"
        "   Exploration bonus β·H(π_θ(·|s_t))\n"
        " • Continuous-to-Discrete Mapping"
    )
    ax.text(38.5, 76, agent_text, fontsize=9.2, color="#bfdbfe", va="top", family="sans-serif", linespacing=1.35)

    # 3. ACTION BOX (Right)
    draw_card(70, 48, 26, 36, "ACTION SPACE  A ∈ {0, 1, 2, 3}", "#2e1a1a", "#dc2626")
    action_text = (
        "Action 0: No Treatment\n"
        " • Unit Cost: 0.0 | Natural balance\n\n"
        "Action 1: Low Treatment\n"
        " • Unit Cost: 1.0 | Bio-control / Spot\n"
        " • Targeted at Aphids & Mites\n\n"
        "Action 2: Medium Treatment\n"
        " • Unit Cost: 2.0 | Targeted Chemical\n"
        " • Standard foliage intervention\n\n"
        "Action 3: High Treatment\n"
        " • Unit Cost: 3.0 | Broad-Spectrum\n"
        " • Emergency knockdown; high drag"
    )
    ax.text(72.5, 76.5, action_text, fontsize=9.2, color="#fecaca", va="top", family="sans-serif", linespacing=1.35)

    # 4. REWARD FUNCTION (Bottom-Center)
    draw_card(36, 8, 59, 34, "MULTI-OBJECTIVE REWARD FORMULATION  R(t)", "#1e2417", "#d97706")
    reward_text = (
        "R_t = + 4.0 · Δ_Pest + 2.5 · (1 - Pest_next / 100)      [Active Pest Reduction Benefit]\n"
        "      + 2.5 · (Crop_Health_next / 100)                   [Crop Tissue Health Preservation]\n"
        "      - C(a) ∈ {0, 1, 2, 3}                               [Operational Treatment Cost]\n"
        "      - P_misuse (Over-spray penalty on low pest)         [Excessive Chemical Penalty]\n"
        "      - P_inaction (Severe unmanaged infestation drag)     [Untreated Crisis Penalty]\n"
        "      + B_harvest (Terminal viability bonus: +10.0)       [Final Yield Viability Bonus]"
    )
    ax.text(38.5, 34, reward_text, fontsize=9.5, color="#fde68a", va="top", family="monospace", linespacing=1.45)

    # Connective Arrows
    arrow_props = dict(arrowstyle="-|>", color="#52b788", lw=3.0, mutation_scale=22)
    arrow_blue = dict(arrowstyle="-|>", color="#3b82f6", lw=3.0, mutation_scale=22)
    arrow_amber = dict(arrowstyle="-|>", color="#f59e0b", lw=3.0, mutation_scale=22)

    # State -> PPO
    ax.annotate("", xy=(36, 68), xytext=(30, 68), arrowprops=arrow_props)
    ax.text(33, 70, "s_t", color="#52b788", fontsize=11, fontweight="bold", ha="center")

    # PPO -> Action
    ax.annotate("", xy=(70, 68), xytext=(64, 68), arrowprops=arrow_blue)
    ax.text(67, 70, "a_t", color="#3b82f6", fontsize=11, fontweight="bold", ha="center")

    # Action -> Reward (downwards)
    ax.annotate("", xy=(83, 42), xytext=(83, 48), arrowprops=dict(arrowstyle="-|>", color="#ef4444", lw=2.5, mutation_scale=20))

    # Reward -> State (Feedback loop back to left)
    ax.annotate("", xy=(17, 30), xytext=(36, 20),
                arrowprops=dict(arrowstyle="-|>", color="#f59e0b", lw=2.5, mutation_scale=20,
                                connectionstyle="arc3,rad=-0.25"))
    ax.text(26, 20, "Next State s_{t+1} & Feedback", color="#f59e0b", fontsize=10, fontweight="bold")

    # Footer note
    ax.text(50, 3.5, "Closed-Loop MDP Horizon: T = 25 Seasonal Decisions | Simulation Framework: AgGym-Compatible Gymnasium Wrapper",
            fontsize=9.5, color="#94a3b8", ha="center")

    plt.tight_layout()
    fig.savefig(save_path, dpi=300, facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    print(f"[Poster Generator] Saved State-Action-Reward Poster to: {save_path}")

if __name__ == "__main__":
    generate_state_action_reward_poster()
