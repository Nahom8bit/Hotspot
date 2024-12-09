# WiFi Extender

A Linux WiFi extender application that allows simultaneous connection to upstream WiFi while broadcasting its own hotspot using a single WiFi card.

## Features

- Single-card WiFi extension
- Graphical user interface for easy management
- Automatic network bridging
- Connection status monitoring
- Client management

## Requirements

### System Dependencies
```bash
sudo apt install hostapd dnsmasq wireless-tools
```

### Python Dependencies
- Python 3.10 or higher
- Poetry for dependency management

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/wifi-extender.git
cd wifi-extender
```

2. Install dependencies:
```bash
poetry install
```

3. Run the application:
```bash
poetry run wifi-extender
```

## Development

1. Install development dependencies:
```bash
poetry install --with dev
```

2. Run tests:
```bash
poetry run pytest
```

3. Format code:
```bash
poetry run black .
```

## License

[MIT License](LICENSE)

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request
