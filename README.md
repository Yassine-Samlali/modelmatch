# ModelMatch LLM v2.0

**ModelMatch LLM** is a lightweight, standalone CLI tool for Windows that analyzes your PC's hardware (System RAM, CPU, and NVIDIA GPU VRAM) and recommends the best open-source Large Language Models (LLMs) your computer can realistically run locally — then lets you **download them in one click**.

It relies on the `psutil` library to scan system RAM, and interfaces with `nvidia-smi` to interrogate your GPU to find out exactly which quantized (GGUF) models like Llama 3, Mistral, Qwen, and DeepSeek are the most compatible with your setup.

---

## 🎯 Features

- **Hardware Detection:** Automatically queries system memory, CPU architecture, and your NVIDIA GPU's Video RAM (VRAM).
- **Clever Matchmaking:** Ranks popular open-source LLMs (Phi-3, Gemma 2, Llama 3, Qwen 2.5, Mixtral) splitting them into "Recommended" and "Too Heavy".
- **Dynamic Suggestions:** Determines if models will run completely on GPU VRAM, partially on GPU, or just CPU-only.
- **Built-in Downloader:** Select any recommended model and download it directly from HuggingFace with a real-time progress bar — no extra tools needed.
- **Beautiful UI:** Developed using `rich` under the hood! Enjoy loading animations, formatted tables, and an interactive colored pager layout directly in your shell.
- **Portable:** Compiles to a single `.exe` with PyInstaller — share it with anyone, no Python install required.

## 📦 Model Database

ModelMatch LLM v2 ships with verified download links for the following GGUF models (Q4_K_M quantization):

| Model | Parameters | Download Size |
|-------|-----------|---------------|
| Phi-3.5 Mini (2026 Edition) | 3.8B | ~2.2 GB |
| Gemma 2 2B Instruct | 2B | ~1.6 GB |
| Llama 3.1 8B Instruct | 8B | ~4.6 GB |
| Mistral 7B v0.3 | 7B | ~4.1 GB |
| Qwen 2.5 14B | 14B | ~8.4 GB |
| DeepSeek-Coder-V2 Lite | 16B (MoE) | ~9.7 GB |
| Command-R (35B) | 35B | ~20.0 GB |
| Llama 3.3 70B Instruct | 70B | ~39.6 GB |
| Mixtral 8x7B | 46.7B (MoE) | ~24.6 GB |

## 🚀 How to Run

You can run ModelMatch LLM directly using Python.

### Prerequisites

- Python 3.10+
- (Optional but Recommended) An NVIDIA GPU with latest drivers installed to enable `nvidia-smi` VRAM probing.

### Installation & Execution

1. Make sure you have Python installed.
2. Install the required Python packages:
   ```bash
   pip install psutil rich
   ```
3. Run the script:
   ```bash
   python modelmatch_llm.py
   ```

### Creating an Executable (.exe)

You can compile this to a completely standalone executable using `pyinstaller`. This is amazing for sharing the application with non-developer friends.

```bash
pip install pyinstaller
pyinstaller --onefile --name ModelMatchLLM modelmatch_llm.py
```
The compiled executable will be located in the `dist/` directory.

## 🤝 How to Clone & Contribute

ModelMatch LLM is completely open-source and welcomes community suggestions. Found a new wildly popular open-source model? Feel free to add it to the `MODEL_DATABASE`!

### Getting the Code

1. Clone the repository:
   ```bash
   git clone https://github.com/Yassine-Samlali/modelmatch.git
   ```
2. Navigate into the directory:
   ```bash
   cd modelmatch
   ```

### Contributing

1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request.

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
