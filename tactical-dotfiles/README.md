# Tactical Dotfiles

A modular, tech-brutalism configuration for Hyprland, Kitty, and Waybar. Designed for paravirtualized QEMU environments with zero border rounding, zero shadows, flat visual pipelines, and high grid-based density.

## Repository Blueprint

```text
tactical-dotfiles/
├── README.md               # Setup documentation & package dependencies
├── install.sh              # One-click deployment script
└── dotfiles/               # Maps directly to ~/.config/
    ├── hypr/
    │   ├── hyprland.conf   # Main entry point
    │   └── configs/
    │       ├── binds.conf  # Keymaps, window controls, navigation
    │       ├── rules.conf  # Rigid window behaviors & layout locking
    │       └── theme.conf  # Vector graphics, sharp borders, zero shadows
    ├── kitty/
    │   └── kitty.conf      # Stark, highly legible developer terminal
    └── waybar/
        ├── config.jsonc    # System telemetry layout
        └── style.css       # Monospace styling sheet
```

## System Requirements & Dependencies

To ensure all bindings and components launch correctly, install the following packages:

- **Window Manager**: `hyprland`
- **Terminal**: `kitty`
- **Application Launcher**: `rofi` (or `rofi-wayland`)
- **Status Bar**: `waybar`
- **Wallpaper Utility**: `hyprpaper`
- **Fonts**: Monospace developer fonts (e.g., `ttf-cascadia-code` or `ttf-jetbrains-mono`)

## Installation

Clone this repository and run the automated deployment script:

```bash
git clone <repository-url>
cd tactical-dotfiles
chmod +x install.sh
./install.sh
```
