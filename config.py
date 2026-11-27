"""
Configuration Module for Vision-Inspired Reinforcement Learning for Adaptive Crop Pest Management.

Provides centralized configuration for:
- Dataset and directory paths (CSV tabular data and Pest Detection image splits)
- Pest classes and pest-aware action space mappings
- Environmental dynamics and multi-objective reward weights
- Vision module hyperparameters (CNN architecture, training parameters)
- PPO reinforcement learning hyperparameters and multi-seed settings
"""

import os
from dataclasses import dataclass, field
from typing import List, Dict, Any


# -----------------------------------------------------------------------------
# Base Directory Resolution
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = CURRENT_DIR

# Check candidate paths for CSV and Pest Detection dataset
CANDIDATE_CSV_PATHS = [
    os.path.join(CURRENT_DIR, "agriculture_dataset.csv"),
    os.path.join(CURRENT_DIR, "..", "agriculture_dataset.csv"),
    os.path.join(CURRENT_DIR, "..", "AgriRL", "agriculture_dataset.csv"),
    "agriculture_dataset.csv"
]

CANDIDATE_IMAGE_DIRS = [
    os.path.join(CURRENT_DIR, "Pest Detection"),
    os.path.join(CURRENT_DIR, "..", "AgriRL_Project", "Pest Detection"),
    os.path.join(CURRENT_DIR, "..", "Pest Detection"),
    "Pest Detection"
]

DEFAULT_CSV_PATH = next((p for p in CANDIDATE_CSV_PATHS if os.path.exists(p)), os.path.join(CURRENT_DIR, "agriculture_dataset.csv"))
DEFAULT_IMAGE_DIR = next((p for p in CANDIDATE_IMAGE_DIRS if os.path.isdir(p)), os.path.join(CURRENT_DIR, "Pest Detection"))


# -----------------------------------------------------------------------------
# Pest Classes & Action Space Definitions
# -----------------------------------------------------------------------------
PEST_CLASSES: List[str] = [
    "aphid",
    "armyworm",
    "beetle",
    "mite",
    "sawfly",
    "stem_borer",
    "stem_fly"
]

# Canonical mapping for varying folder names in train/test splits
FOLDER_TO_CLASS_MAP: Dict[str, str] = {
    "aphid_train": "aphid",
    "aphid_test": "aphid",
    "armyworm_train": "armyworm",
    "armyworm_test": "armyworm",
    "beetle_train": "beetle",
    "beetle_test": "beetle",
    "mite_train": "mite",
    "mite_test": "mite",
    "sawfly_train": "sawfly",
    "sawfly_test": "sawfly",
    "stemborder_train": "stem_borer",
    "stem_borer_test": "stem_borer",
    "stemfly_train": "stem_fly",
    "stem_fly_test": "stem_fly"
}

# Pest-Aware 4-Action Space (0: None, 1: Low, 2: Medium, 3: High)
ACTION_NAMES: Dict[int, str] = {
    0: "No Treatment",
    1: "Low Treatment (Biological / Spot Spray)",
    2: "Medium Treatment (Targeted Chemical)",
    3: "High Treatment (Broad-Spectrum Chemical)"
}

# Operational/Material Cost associated with each action (unit costs: 0, 1, 2, 3)
ACTION_COSTS: Dict[int, float] = {
    0: 0.0,
    1: 1.0,
    2: 2.0,
    3: 3.0
}


# -----------------------------------------------------------------------------
# Configuration Dataclasses
# -----------------------------------------------------------------------------
@dataclass
class VisionConfig:
    """Hyperparameters for CNN Pest Classifier."""
    image_dir: str = DEFAULT_IMAGE_DIR
    image_size: int = 128
    batch_size: int = 64
    num_classes: int = len(PEST_CLASSES)
    learning_rate: float = 1e-3
    num_epochs: int = 50
    weight_decay: float = 1e-4
    model_save_path: str = os.path.join(CURRENT_DIR, "models", "pest_cnn.pt")
    prob_cache_path: str = os.path.join(CURRENT_DIR, "models", "pest_prob_cache.npz")
    metrics_save_path: str = os.path.join(CURRENT_DIR, "results", "vision_metrics.json")
    confusion_matrix_path: str = os.path.join(CURRENT_DIR, "results", "confusion_matrix.npy")
    use_mock: bool = False


@dataclass
class EnvConfig:
    """Hyperparameters for Agricultural Gymnasium Environment."""
    csv_path: str = DEFAULT_CSV_PATH
    max_steps_per_episode: int = 25  # Standard 25-week seasonal decision horizon
    crop_health_threshold_success: float = 70.0  # Harvest viability threshold (%)
    pest_damage_threshold_success: float = 25.0  # Max acceptable pest damage at harvest (%)
    chemical_misuse_penalty: float = 2.5         # Penalty for unnecessary chemical spraying
    untreated_pest_penalty_factor: float = 0.05  # Progressive penalty for unmanaged high pest
    harvest_bonus: float = 10.0                  # Terminal bonus for healthy crop harvest
    phytotoxicity_high_spray: float = 3.5        # Plant tissue damage caused by broad-spectrum spray
    mode: str = "multimodal"                     # "multimodal" (16-dim) or "tabular" (9-dim)
    use_mock: bool = False


@dataclass
class RLConfig:
    """Hyperparameters for PPO Agent and Multi-Seed Evaluation."""
    seeds: List[int] = field(default_factory=lambda: [0, 1, 2])
    total_timesteps: int = 30000
    learning_rate: float = 3e-4
    n_steps: int = 512
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.02                       # Exploration entropy bonus
    eval_episodes: int = 40                      # Evaluation episodes per seed
    moving_avg_window: int = 50                  # Window for moving average reward
    perturbation_noise_std: float = 0.15         # Noise injected during robustness test
    results_dir: str = os.path.join(CURRENT_DIR, "results")
    models_dir: str = os.path.join(CURRENT_DIR, "models")
    plots_dir: str = os.path.join(CURRENT_DIR, "plots")


@dataclass
class ProjectConfig:
    """Master Configuration container."""
    vision: VisionConfig = field(default_factory=VisionConfig)
    env: EnvConfig = field(default_factory=EnvConfig)
    rl: RLConfig = field(default_factory=RLConfig)

    def ensure_directories(self):
        """Ensures that models, results, and plots directories exist."""
        for d in [self.rl.results_dir, self.rl.models_dir, self.rl.plots_dir]:
            os.makedirs(d, exist_ok=True)


def get_default_config() -> ProjectConfig:
    """Returns a fully instantiated default ProjectConfig with directories created."""
    cfg = ProjectConfig()
    cfg.ensure_directories()
    return cfg
