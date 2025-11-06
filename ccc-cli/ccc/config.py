"""Configuration management for CCC CLI"""
import os
import json
from pathlib import Path

class Config:
    """Manages CCC configuration"""

    def __init__(self):
        self.config_dir = Path.home() / ".ccc"
        self.config_file = self.config_dir / "config.json"
        self.credentials_file = self.config_dir / "credentials.json"

        # Ensure config directory exists
        self.config_dir.mkdir(exist_ok=True, mode=0o700)

        # Load or initialize config
        self._config = self._load_config()

    def _load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                return json.load(f)
        return {}

    def save(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self._config, f, indent=2)
        os.chmod(self.config_file, 0o600)

    def get(self, key, default=None):
        """Get configuration value"""
        return self._config.get(key, default)

    def set(self, key, value):
        """Set configuration value"""
        self._config[key] = value
        self.save()

    def get_credentials(self):
        """Load cached credentials"""
        if not self.credentials_file.exists():
            return None

        with open(self.credentials_file, 'r') as f:
            return json.load(f)

    def save_credentials(self, credentials):
        """Save credentials to cache"""
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=2)
        os.chmod(self.credentials_file, 0o600)

    def clear_credentials(self):
        """Remove cached credentials"""
        if self.credentials_file.exists():
            self.credentials_file.unlink()

# Global config instance
config = Config()
