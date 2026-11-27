# AgriRL: Vision-Based Reinforcement Learning for Adaptive Crop Pest Management

An end-to-end precision agriculture decision-support system coupling **Deep Residual Computer Vision** and **Proximal Policy Optimization (PPO)** in an **AgGym-compatible Gymnasium environment**.

---

## 🌾 Project Overview & Key Upgrades

| Dimension | Mini-Project Baseline | End-Semester Upgrade (AgriRL) |
| :--- | :--- | :--- |
| **Observation Modality** | Tabular only ($S \in \mathbb{R}^9$) from sensor CSV | **Multimodal Fusion ($S \in \mathbb{R}^{16}$)**: 9 Tabular + 7 CNN Pest Probabilities |
| **Visual Perception** | None (abstract damage numbers) | **Lightweight Residual CNN (1.2M params)** trained on 4,187 images with **stratified 70:15:15 split** |
| **Action Space** | Generic abstract intensity ($A \in \{0, 1, 2, 3\}$) | **Pest-Aware Adaptive Treatments**: Species-dependent efficacy (Bio, Targeted, Broad-Spectrum) |
| **Statistical Rigor** | Single-seed training | **Multi-Seed Protocol (seeds 0, 1, 2)** with sample mean $\pm$ std, **95% Confidence Intervals**, and **Robustness Gap** |
| **Exploration Analysis** | Not reported | **Policy Entropy Decay Schedule $\mathcal{H}(\pi_\theta)$**, action distribution, and PPO diagnostic tracking |
| **Academic Deliverables** | Basic scripts | Complete **35-Section Word Report (.docx)**, **30-Slide PPTX**, SAR Poster, Architecture Diagram, and Web Dashboard |

---

## 📂 Repository Structure

```text
AgriRL_Project/
├── config.py                 # Centralized configuration, hyperparameter dataclasses, action maps
├── vision_module.py          # PyTorch Residual CNN, stratified 70:15:15 split, 7x7 confusion matrix
├── env_aggym_wrapper.py      # AgGym biotic stress Gymnasium wrapper (Multimodal & Tabular modes)
├── train_and_eval.py         # Multi-seed PPO engine (Random vs Tabular PPO vs Multimodal PPO)
├── generate_plots.py         # 6 publication-ready figures (300 DPI) for report and PPT
├── generate_sar_poster.py    # State-Action-Reward Closed-Loop Infographic Poster
├── generate_architecture_diagram.py # Comprehensive System Architecture Diagram
├── generate_academic_report.py      # Compiles complete 35-chapter Word Project Report (.docx)
├── generate_academic_presentation.py# Compiles complete 30-slide PowerPoint presentation (.pptx)
├── viva_preparation_guide.md # Complete viva voce Q&A guide with 2/3/5-minute speech scripts
├── run_web_simulator.py      # Interactive web dashboard server with live image inference
├── web/                      # HTML, CSS, JS frontend assets
├── models/                   # Trained CNN (.pt) and PPO (.zip) model checkpoints
├── results/                  # Evaluation JSONs, confusion matrix (.npy), split summary
├── plots/                    # High-resolution output figures (300 DPI PNGs)
├── documentation/            # Generated Academic Report (.docx) & Presentation (.pptx)
├── requirements.txt          # Dependency specifications
└── README.md                 # Project documentation and execution instructions
```

---

## 🚀 Step-by-Step Execution Guide

### 1. Environment Setup & Verification
Ensure Python 3.10+ is installed with the required libraries:
```bash
pip install -r requirements.txt
```

### 2. Train the Computer Vision Module (Stratified 70:15:15 Split)
Train the lightweight Residual CNN on the 4,187 images across the 7 pest classes:
```bash
python AgriRL_Project/vision_module.py --epochs 4 --batch-size 64
```
- Outputs:
  - `models/pest_cnn.pt`: Best model weights based on validation accuracy
  - `results/split_summary.json`: Exact sample breakdown (70% Train: 2,931 | 15% Val: 626 | 15% Test: 630)
  - `results/vision_metrics.json`: Unseen test accuracy, macro-F1, per-class precision and recall
  - `results/confusion_matrix.npy`: 7x7 confusion matrix
  - `models/pest_prob_cache.npz`: Pre-computed empirical probability distributions for high-speed simulation

To test a single leaf image:
```bash
python AgriRL_Project/vision_module.py --predict "AgriRL_Project/Pest Detection/test/aphid_test/aphid_0.png"
```

### 3. Run Multi-Seed PPO Training & Baseline Comparison
Executes matched-budget training and deterministic held-out evaluation across seeds 0, 1, 2 for:
1. Random Policy Baseline
2. Tabular-Only PPO (Mini-Project Baseline)
3. Multimodal Vision PPO (Proposed Model)
```bash
python AgriRL_Project/train_and_eval.py --timesteps 15000 --eval-episodes 30 --seeds 0 1 2
```
- Outputs:
  - `models/multimodal_vision_ppo.zip` & `models/tabular_ppo.zip`
  - `results/evaluation_metrics.json`: Returns, 95% CIs, success rates, violation rates, robustness gap
  - `results/training_histories.json`: Episode logs, policy entropy trajectories, PPO losses

### 4. Generate Publication-Quality Visualizations
Generate all 6 evaluation plots at 300 DPI:
```bash
python AgriRL_Project/generate_plots.py
```
- Generated Figures in `plots/`:
  1. `fig1_learning_curves.png`: Cumulative episode return, moving average (window=50), and uncertainty band
  2. `fig2_baseline_comparison.png`: Matched-step convergence comparison across models
  3. `fig3_success_and_constraint_rates.png`: Task Success Rate vs Chemical Constraint Violation Rate
  4. `fig4_exploration_schedule.png`: PPO policy entropy decay curve ($\mathcal{H}(\pi_\theta)$)
  5. `fig5_evaluation_boxplots.png`: Statistical distribution of evaluation returns across seeds
  6. `fig6_confusion_matrix_and_action_dist.png`: 7x7 CNN Confusion Matrix & Action Breakdown

### 5. Generate Architecture & Poster Diagrams
```bash
python AgriRL_Project/generate_sar_poster.py
python AgriRL_Project/generate_architecture_diagram.py
```
- Outputs:
  - `plots/state_action_reward_poster.png`
  - `plots/system_architecture_diagram.png`

### 6. Compile Academic Report & Presentation Deck
```bash
python AgriRL_Project/generate_academic_report.py
python AgriRL_Project/generate_academic_presentation.py
```
- Outputs:
  - `documentation/AgriRL_Academic_Project_Report.docx`: 35-chapter Word document
  - `documentation/AgriRL_Academic_Presentation.pptx`: 30-slide presentation deck

### 7. Launch Interactive Web Simulator
```bash
python AgriRL_Project/run_web_simulator.py
```
Navigate to `http://localhost:8501` to test the visual dashboard, upload leaf images, view live CNN pest identification, and observe PPO treatment recommendations in real time.

---

## 📊 Summary of Benchmark Results

| Model Evaluated | Mean Return ($\pm \text{Std}$) | 95% Confidence Interval | Task Success Rate | Constraint Violations | Robustness Gap ($\Delta_{\text{rob}}$) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Random Policy Baseline** | $19.18 \pm 1.94$ | $\pm 0.81$ | $28.9\%$ | $57.7\%$ | $+2.38$ |
| **Tabular-Only PPO (Mini-Project)** | $60.29 \pm 11.56$ | $\pm 4.82$ | $2.2\%$ | $\mathbf{0.0\%}$ | $-7.51$ |
| **Multimodal Vision PPO (AgriRL)** | $\mathbf{69.50 \pm 1.15}$ | $\mathbf{\pm 0.48}$ | $\mathbf{33.3\%}$ | $15.6\%$ | $\mathbf{-1.67}$ |

*Key Findings:*
1. **Multimodal Grounding:** Grounding PPO in visual pest identity increases average return by **+9.21 units** and reduces return variance by **10x** ($s=1.15$ vs $s=11.56$), demonstrating high training stability across seeds.
2. **Harvest Viability:** Multimodal Vision PPO achieves a **33.3% harvest success rate** under strict economic thresholds, compared to only 2.2% for the blind tabular agent.
3. **Pesticide Restraint:** Chemical constraint violations drop by **73%** relative to the random baseline, verifying that the policy learns to avoid unnecessary broad-spectrum spraying on clean crops.
