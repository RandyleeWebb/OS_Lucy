# 🧬 Ollama Coding Agent (Llama-3-FineTune)

A local agentic coding assistant powered by **Ollama** and integrated with **Helix-OS Code Training Studio**. This project implements a ReAct-based agent that reads/writes files in the workspace and supports fine-tuning.

## 🚀 Features
- **ReAct Reason-Act Loop**: Thinking -> Action (Tool Call) -> Observation.
- **File System Tools**: Reads, writes, and lists files recursively in your project directory.
- **Ollama Integration**: Runs against a custom registered `ollama-coder` model.
- **Helix-OS Studio Integration**: Ready for import and telemetry monitoring inside the Helix AGI-OS Cortical Dashboard.

## 🛠️ Installation & Setup
Please see [INSTALL.md](file:///d:/3D_Object/ollhama-trained%20ai/INSTALL.md) for full configuration steps.

### Windows
```powershell
.\start.bat
```

### Unix/macOS
```bash
chmod +x setup.sh
./setup.sh
```

## 🌌 Importing into Helix Code Training Studio
1. Open the Helix-OS dashboard at `http://localhost:3000`.
2. Click **Connect AI Project** -> **Local Folder**.
3. Select this folder (`d:\3D_Object\ollhama-trained ai`).
4. Helix-OS will scan and discover the blueprint, entrypoint (`train.py`), config (`configs/training_config.yaml`), and packages.
5. You can now use the Monaco editor inside Helix-OS to view/edit files and run fine-tuning loops with live telemetry visualizations!
