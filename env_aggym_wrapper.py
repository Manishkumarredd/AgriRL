"""
Agricultural Gymnasium Environment Wrapper for Pest Management.
Integrates AgGym Biotic Stress Dynamics, Multimodal State Fusion, and Pest-Aware Action Space.

Features:
1. Standards-compliant Gymnasium Environment (gymnasium.Env).
2. Dual observation modes:
   - "multimodal": 16-dimensional vector [9 Tabular Agro-climatic Features + 7 CNN Pest Probabilities]
   - "tabular": 9-dimensional vector [Tabular Agro-climatic Features only] (Mini-project baseline)
3. 5-Discrete Pest-Aware Treatment Actions:
   - 0: No Treatment
   - 1: Bio-Control (Parasitoids/Predators; targeted at aphids & mites)
   - 2: Targeted Bt / Bio-Insecticide (Bt spray; targeted at defoliators: armyworm, sawfly)
   - 3: Targeted Systemic Insecticide (Translaminar chemical; targeted at stem borers & stem flies)
   - 4: Broad-Spectrum Chemical Knockdown (Emergency broad knockdown; high cost & phytotoxicity)
4. State-Dependent Agronomic & Biotic Dynamics:
   - Weather-influenced pest reproduction (warmth & humidity accelerate reproduction)
   - Pest-specific efficacy matrix based on target biological mechanism
   - Plant injury, natural vegetative recovery, and chemical phytotoxicity/drag
5. Multi-Objective Reward Function:
   - Pest suppression reward + Crop health reward - Treatment cost - Chemical misuse penalty
     - Inaction penalty during severe infestation + Terminal harvest bonus
6. Constraint Violation Tracking:
   - Flags excessive chemical application on healthy crops or misapplication of targeted chemicals.
"""

import os
from typing import Dict, Any, Tuple, Optional, Union
import numpy as np
import pandas as pd
import gymnasium as gym
from gymnasium import spaces

from config import (
    PEST_CLASSES,
    ACTION_NAMES,
    ACTION_COSTS,
    EnvConfig,
    get_default_config
)


class AgGymWrapperEnv(gym.Env):
    """
    AgGym Agricultural Pest Management Gymnasium Environment.
    Wraps sequential biotic-stress agro-ecological dynamics with multimodal vision support.
    """
    metadata = {"render_modes": ["human"], "render_fps": 10}

    # Agronomic Pest Efficacy Matrix: [Action 0..3] x [Pest 0..6]
    # Rows: Actions (0: None, 1: Low Bio/Spot, 2: Medium Targeted, 3: High Broad-Spectrum)
    # Cols: Pests ("aphid", "armyworm", "beetle", "mite", "sawfly", "stem_borer", "stem_fly")
    BASE_EFFICACY_MATRIX = np.array([
        # aphid, armyworm, beetle,  mite, sawfly, stem_borer, stem_fly
        [  0.00,     0.00,   0.00,  0.00,   0.00,       0.00,     0.00],  # 0: No Treatment
        [  0.78,     0.32,   0.35,  0.75,   0.35,       0.15,     0.18],  # 1: Low Treatment (Bio/Spot)
        [  0.72,     0.82,   0.75,  0.68,   0.80,       0.65,     0.68],  # 2: Medium Treatment (Targeted)
        [  0.92,     0.94,   0.90,  0.88,   0.92,       0.86,     0.88],  # 3: High Treatment (Broad-Spectrum)
    ], dtype=np.float32)

    def __init__(
        self,
        config: Optional[EnvConfig] = None,
        mode: Optional[str] = None,
        prob_cache_path: Optional[str] = None,
        render_mode: Optional[str] = None,
        seed: Optional[int] = 42
    ):
        super().__init__()
        self.config = config if config is not None else get_default_config().env
        self.mode = (mode if mode is not None else self.config.mode).lower()
        self.render_mode = render_mode
        self.current_step = 0
        self.cumulative_violations = 0
        self.cumulative_treatment_cost = 0.0

        # Define 4 Discrete Actions (0: None, 1: Low, 2: Med, 3: High)
        self.action_space = spaces.Discrete(4)

        # Observation Space:
        # Multimodal: Box(16,) -> [9 tabular features, 7 CNN class probabilities]
        # Tabular:    Box(9,)  -> [9 tabular features]
        if self.mode == "multimodal":
            self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(16,), dtype=np.float32)
        else:
            self.observation_space = spaces.Box(low=0.0, high=1.0, shape=(9,), dtype=np.float32)

        # Load or generate tabular dataset
        self.dataset = self._load_or_mock_dataset()

        # Load CNN probability cache if available
        cache_file = prob_cache_path if prob_cache_path else os.path.join(
            os.path.dirname(self.config.csv_path), "models", "pest_prob_cache.npz"
        )
        self.prob_cache = self._load_prob_cache(cache_file)

        # State storage
        self.state: Dict[str, Any] = {}
        self.current_pest_probs = np.zeros(7, dtype=np.float32)
        self.true_pest_idx = 0

        self.reset(seed=seed)

    def _load_prob_cache(self, path: str) -> Optional[Dict[str, np.ndarray]]:
        """Loads cached empirical CNN probabilities for rapid sampling."""
        candidates = [
            path,
            os.path.join(os.path.dirname(__file__), "models", "pest_prob_cache.npz"),
            "models/pest_prob_cache.npz"
        ]
        for c in candidates:
            if c and os.path.exists(c):
                try:
                    data = np.load(c)
                    return {k: data[k] for k in data.files}
                except Exception:
                    pass
        return None

    def _load_or_mock_dataset(self) -> pd.DataFrame:
        """Loads real agricultural CSV or creates synthetic realistic dataset."""
        candidates = [
            self.config.csv_path,
            os.path.join(os.path.dirname(__file__), "agriculture_dataset.csv"),
            os.path.join(os.path.dirname(__file__), "..", "AgriRL", "agriculture_dataset.csv"),
            "agriculture_dataset.csv"
        ]

        if not self.config.use_mock:
            for p in candidates:
                if p and os.path.exists(p):
                    try:
                        cols = [
                            "Pest_Damage", "Crop_Stress_Indicator", "Temperature",
                            "Humidity", "Soil_Moisture", "NDVI", "Crop_Growth_Stage",
                            "Pest_Hotspots", "Rainfall"
                        ]
                        df = pd.read_csv(p, usecols=lambda c: c in cols)
                        if "Pest_Damage" in df.columns:
                            # Normalize & clean
                            df["Crop_Stress"] = df["Crop_Stress_Indicator"].clip(0.0, 100.0)
                            df["Crop_Health"] = (100.0 - df["Crop_Stress"]).clip(0.0, 100.0)
                            return df
                    except Exception:
                        pass

        # Synthetic fallback
        N = 2000
        np.random.seed(42)
        return pd.DataFrame({
            "Pest_Damage": np.random.uniform(5.0, 85.0, N),
            "Crop_Health": np.random.uniform(30.0, 95.0, N),
            "Crop_Stress": np.random.uniform(10.0, 70.0, N),
            "Temperature": np.random.uniform(18.0, 38.0, N),
            "Humidity": np.random.uniform(30.0, 90.0, N),
            "Soil_Moisture": np.random.uniform(15.0, 75.0, N),
            "NDVI": np.random.uniform(0.25, 0.85, N),
            "Crop_Growth_Stage": np.random.choice([1, 2, 3, 4], size=N),
            "Pest_Hotspots": np.random.choice([0, 1], p=[0.75, 0.25], size=N),
            "Rainfall": np.random.uniform(0.0, 45.0, N)
        })

    def _sample_pest_probabilities(self, ground_truth_class: int) -> np.ndarray:
        """
        Samples realistic CNN softmax probabilities for the current pest infestation.
        Uses cached CNN test predictions if available, else Dirichlet distribution with ~85% accuracy.
        """
        if self.prob_cache and f"class_{ground_truth_class}" in self.prob_cache:
            class_vecs = self.prob_cache[f"class_{ground_truth_class}"]
            if len(class_vecs) > 0:
                idx = np.random.randint(0, len(class_vecs))
                return class_vecs[idx].copy()

        # Realistic synthetic CNN probability distribution (noisy perception)
        alpha = np.ones(7, dtype=np.float32) * 0.15
        alpha[ground_truth_class] = 4.5
        probs = np.random.dirichlet(alpha).astype(np.float32)
        return probs

    def _get_obs(self) -> np.ndarray:
        """Constructs observation vector based on active mode."""
        tabular_obs = np.array([
            self.state["pest_damage"] / 100.0,
            self.state["crop_health"] / 100.0,
            self.state["crop_stress"] / 100.0,
            self.state["temperature"] / 50.0,
            self.state["humidity"] / 100.0,
            self.state["soil_moisture"] / 100.0,
            np.clip(self.state["ndvi"], 0.0, 1.0),
            (self.state["crop_growth_stage"] - 1.0) / 3.0,
            float(self.state["pest_hotspots"])
        ], dtype=np.float32)

        if self.mode == "multimodal":
            obs = np.concatenate([tabular_obs, self.current_pest_probs])
        else:
            obs = tabular_obs

        return np.clip(obs, 0.0, 1.0).astype(np.float32)

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Resets the environment for a new 25-step agricultural season."""
        super().reset(seed=seed)
        if seed is not None:
            np.random.seed(seed)

        self.current_step = 0
        self.cumulative_violations = 0
        self.cumulative_treatment_cost = 0.0

        # Sample initial tabular state from dataset
        row_idx = np.random.randint(0, len(self.dataset))
        row = self.dataset.iloc[row_idx]

        # Sample latent ground-truth pest infesting this field
        self.true_pest_idx = np.random.randint(0, 7)
        self.current_pest_probs = self._sample_pest_probabilities(self.true_pest_idx)

        self.state = {
            "pest_damage": float(row.get("Pest_Damage", np.random.uniform(20.0, 60.0))),
            "crop_health": float(row.get("Crop_Health", 75.0)),
            "crop_stress": float(row.get("Crop_Stress", 25.0)),
            "temperature": float(row.get("Temperature", 27.0)),
            "humidity": float(row.get("Humidity", 65.0)),
            "soil_moisture": float(row.get("Soil_Moisture", 40.0)),
            "ndvi": float(row.get("NDVI", 0.60)),
            "crop_growth_stage": float(row.get("Crop_Growth_Stage", 2.0)),
            "pest_hotspots": float(row.get("Pest_Hotspots", 0.0)),
            "rainfall": float(row.get("Rainfall", 10.0)),
            "true_pest_name": PEST_CLASSES[self.true_pest_idx]
        }

        obs = self._get_obs()
        info = {
            "step": self.current_step,
            "true_pest": self.state["true_pest_name"],
            "pest_damage": self.state["pest_damage"],
            "crop_health": self.state["crop_health"],
            "violations": 0
        }
        return obs, info

    def _compute_treatment_efficacy(self, action: int) -> float:
        """
        Computes dynamic, state- and pest-specific treatment efficacy.
        Incorporates biological target matching, weather conditions, and infestation severity.
        """
        if action == 0:
            return 0.0

        # Base biological efficacy on target pest species
        base_eff = float(self.BASE_EFFICACY_MATRIX[action, self.true_pest_idx])

        # Weather factor: High humidity (>75%) washes off foliage sprays; extreme heat degrades biopesticides
        temp = self.state["temperature"]
        hum = self.state["humidity"]
        weather_factor = 1.0
        if hum > 75.0:
            weather_factor *= 0.90
        if action in [1, 2] and temp > 36.0:  # Bio-controls degrade under extreme temperature
            weather_factor *= 0.85

        # Pest severity factor: Bio-control drops effectiveness if pests are overwhelming (>60%)
        pest = self.state["pest_damage"]
        severity_factor = 1.0
        if action == 1 and pest > 55.0:
            severity_factor = max(0.40, 1.0 - 0.60 * ((pest - 55.0) / 45.0))

        efficacy = base_eff * weather_factor * severity_factor
        return float(np.clip(efficacy, 0.05, 0.96))

    def step(self, action: int) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Executes one weekly agricultural decision step."""
        assert self.action_space.contains(action), f"Invalid action: {action}"

        pest_prev = self.state["pest_damage"]
        health_prev = self.state["crop_health"]
        temp = self.state["temperature"]
        hum = self.state["humidity"]
        hotspots = self.state["pest_hotspots"]

        # 1. Treatment Efficacy
        efficacy = self._compute_treatment_efficacy(action)

        # 2. Pest Population Dynamics (Reproduction & Suppression)
        # Warm, humid conditions accelerate reproduction
        temp_mult = 1.30 if (22.0 <= temp <= 35.0) else 0.80
        hum_mult = 1.25 if hum >= 60.0 else 0.85
        hotspot_mult = 1.35 if hotspots == 1 else 1.0
        natural_pest_growth = 4.2 * temp_mult * hum_mult * hotspot_mult

        # Efficacy suppresses existing pest population and residual reproduction
        suppressed_pest = pest_prev * (1.0 - efficacy)
        resurgence = natural_pest_growth * max(0.12, 1.0 - 0.70 * efficacy)
        pest_next = float(np.clip(suppressed_pest + resurgence, 0.0, 100.0))

        # 3. Crop Health Response & Phytotoxicity
        # Tissue injury inflicted by remaining pests
        pest_injury = (pest_next / 100.0) * 7.0

        # Natural vegetative recovery when pest burden is light
        vegetative_recovery = max(0.0, 1.0 - (pest_next / 100.0)) * 3.2

        # Phytotoxicity / Chemical Drag from chemical applications
        phytotoxicity = 0.0
        if action == 3:  # High Treatment (Broad-spectrum chemical)
            phytotoxicity = self.config.phytotoxicity_high_spray
            if pest_prev < 25.0:  # Severe scorch on clean crop
                phytotoxicity += 2.5
        elif action == 2:  # Medium Treatment (Targeted chemical)
            phytotoxicity = 1.0
            if pest_prev < 15.0:
                phytotoxicity += 1.2

        health_next = float(np.clip(health_prev + vegetative_recovery - pest_injury - phytotoxicity, 0.0, 100.0))
        stress_next = 100.0 - health_next

        # 4. Multi-Objective Reward & Constraint Tracking
        # A. Pest reduction benefit
        pest_reduction = max(0.0, pest_prev - pest_next) / 100.0
        pest_reward = (4.0 * pest_reduction) + (2.5 * (1.0 - pest_next / 100.0))

        # B. Crop health preservation benefit
        health_reward = 2.5 * (health_next / 100.0)

        # C. Operational treatment cost
        treatment_cost = ACTION_COSTS[action]
        self.cumulative_treatment_cost += treatment_cost

        # D. Constraint Violations & Over-spray / Misuse Penalties
        # Violation 1: Applying High Treatment (Action 3) when pest damage < 30%
        # Violation 2: Applying Medium Treatment (Action 2) when pest damage < 15%
        # Violation 3: Inaction (Action 0) during pest crisis > 50%
        is_violation = False
        misuse_penalty = 0.0

        if action == 3 and pest_prev < 30.0:
            is_violation = True
            misuse_penalty = self.config.chemical_misuse_penalty + 1.5
        elif action == 2 and pest_prev < 15.0:
            is_violation = True
            misuse_penalty = self.config.chemical_misuse_penalty
        elif action == 1 and pest_prev < 10.0:
            is_violation = True
            misuse_penalty = 0.8

        if is_violation:
            self.cumulative_violations += 1

        # E. Severe Untreated Pest Penalty
        inaction_penalty = 0.0
        if action == 0 and pest_prev > 45.0:
            inaction_penalty = 1.5 + (pest_prev - 45.0) * self.config.untreated_pest_penalty_factor
        elif action == 1 and pest_prev > 65.0:
            inaction_penalty = 1.2  # Bio-control alone is biologically insufficient during a crisis

        # F. Terminal Harvest Bonus (awarded at end of season if crop survived healthily)
        self.current_step += 1
        terminated = bool(health_next <= 5.0)  # Crop collapse
        truncated = bool(self.current_step >= self.config.max_steps_per_episode)

        harvest_bonus = 0.0
        task_success = False
        if (terminated or truncated) and (not terminated):
            if health_next >= self.config.crop_health_threshold_success and pest_next <= self.config.pest_damage_threshold_success:
                harvest_bonus = self.config.harvest_bonus
                task_success = True

        reward = float(
            pest_reward
            + health_reward
            - treatment_cost
            - misuse_penalty
            - inaction_penalty
            + harvest_bonus
        )

        # Update environment state
        self.state["pest_damage"] = pest_next
        self.state["crop_health"] = health_next
        self.state["crop_stress"] = stress_next
        self.state["temperature"] = float(np.clip(temp + np.random.uniform(-1.0, 1.0), 10.0, 45.0))
        self.state["humidity"] = float(np.clip(hum + np.random.uniform(-2.0, 2.0), 20.0, 95.0))
        self.state["ndvi"] = float(np.clip(0.15 + 0.72 * (health_next / 100.0) + np.random.uniform(-0.02, 0.02), 0.0, 1.0))

        # Advance phenological stage
        if self.current_step % 7 == 0:
            self.state["crop_growth_stage"] = min(4.0, self.state["crop_growth_stage"] + 1.0)

        # Resample visual probabilities for new step (incorporating environmental noise)
        self.current_pest_probs = self._sample_pest_probabilities(self.true_pest_idx)

        obs = self._get_obs()
        info = {
            "step": self.current_step,
            "action": action,
            "action_name": ACTION_NAMES[action],
            "efficacy": efficacy,
            "pest_damage": pest_next,
            "crop_health": health_next,
            "treatment_cost": treatment_cost,
            "is_violation": is_violation,
            "cumulative_violations": self.cumulative_violations,
            "cumulative_treatment_cost": self.cumulative_treatment_cost,
            "task_success": task_success,
            "true_pest": self.state["true_pest_name"],
            "reward": reward
        }

        return obs, reward, terminated, truncated, info

    def render(self):
        """Displays readable step status."""
        print(f"[Step {self.current_step:02d}] Pest: {self.state['pest_damage']:.1f}% ({self.state['true_pest_name']}) | "
              f"Health: {self.state['crop_health']:.1f}% | NDVI: {self.state['ndvi']:.2f}")


# Re-register environments in Gymnasium registry
gym.register(
    id="AgGymMultimodal-v1",
    entry_point="env_aggym_wrapper:AgGymWrapperEnv",
    max_episode_steps=25,
    kwargs={"mode": "multimodal"}
)

gym.register(
    id="AgGymTabular-v1",
    entry_point="env_aggym_wrapper:AgGymWrapperEnv",
    max_episode_steps=25,
    kwargs={"mode": "tabular"}
)
