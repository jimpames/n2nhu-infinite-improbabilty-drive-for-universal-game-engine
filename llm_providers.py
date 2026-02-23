"""
N2NHU Infinite Improbability Drive - LLM Providers
====================================================
Four LLM providers in priority order:
  1. GPT4All  (local, free, private)
  2. Claude   (cloud, best quality)
  3. HuggingFace (cloud, free tier)
  4. Template (always works, no dependencies)

Each provider implements one method:
    generate(world_name, room_name) -> str

The orchestrator tries each in order until one succeeds.
The engine never knows which provider ran.

N2NHU Labs for Applied Artificial Intelligence
"""

import requests
import json
import time
import re
from typing import Optional
from abc import ABC, abstractmethod


# ── The prompt that drives all providers ─────────────────────
# Tested with Llama 3 8B — produces rich, world-aware descriptions
# "Do NOT end with What would you like to do" — engine adds that itself

ROOM_PROMPT = """You are generating room descriptions for a text-based adventure game named {world_name}.

Generate an atmospheric, immersive description for the {room_name}.

Requirements:
- 3 to 5 sentences
- Vivid sensory details: sight, sound, smell, texture
- Match the tone and setting of {world_name} precisely  
- Do NOT end with "What would you like to do?" or any question
- Do NOT mention game mechanics or controls
- Write only the description, nothing else, no preamble

Description:"""


def _clean_response(text: str) -> str:
    """
    Clean LLM output — strip preamble, trailing prompts, excess whitespace.
    Some models echo the prompt or add 'Description:' prefix.
    """
    # Remove common preamble patterns
    patterns = [
        r'^Description:\s*',
        r'^Here is.*?:\s*',
        r'^Sure.*?:\s*',
        r'^Welcome to.*?!\s*',   # keep content, just normalize
        r'What would you like to do\??\s*$',
        r'What do you do\??\s*$',
        r'>\s*$',
    ]
    text = text.strip()
    for pattern in patterns:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE).strip()
    
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# ── Abstract base ────────────────────────────────────────────

class LLMProvider(ABC):
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider can be reached."""
        pass

    @abstractmethod
    def generate(self, world_name: str, room_name: str) -> Optional[str]:
        """Generate a room description. Returns None on failure."""
        pass


# ── Provider 1: GPT4All (local) ──────────────────────────────

class GPT4AllProvider(LLMProvider):
    """
    Connects to GPT4All running locally.
    GPT4All exposes an OpenAI-compatible API on port 4891.
    No API key required. Completely private.
    
    Supported models (from your localhost:4891/v1/models):
      - Llama 3 8B Instruct      (best for game descriptions)
      - Llama 3.2 3B Instruct    (faster, still good)
      - Llama 3.1 8B 128k        (long context)
      - Mistral Instruct         (good alternative)
      - Phi-3 Mini               (fastest, lighter)
    """

    def __init__(self, host: str = 'localhost', port: int = 4891,
                 model: str = 'Llama 3 8B Instruct', timeout: int = 60):
        self.host    = host
        self.port    = port
        self.model   = model
        self.timeout = timeout
        self.base_url = f'http://{host}:{port}/v1'

    @property
    def name(self) -> str:
        return f'GPT4All ({self.model})'

    def is_available(self) -> bool:
        try:
            r = requests.get(f'{self.base_url}/models', timeout=5)
            return r.status_code == 200
        except Exception:
            return False

    def list_models(self):
        """Return available model IDs from GPT4All."""
        try:
            r = requests.get(f'{self.base_url}/models', timeout=5)
            data = r.json()
            return [m['id'] for m in data.get('data', [])]
        except Exception:
            return []

    def generate(self, world_name: str, room_name: str) -> Optional[str]:
        prompt = ROOM_PROMPT.format(world_name=world_name, room_name=room_name)
        try:
            payload = {
                'model':       self.model,
                'messages':    [{'role': 'user', 'content': prompt}],
                'max_tokens':  400,
                'temperature': 0.8,
            }
            r = requests.post(
                f'{self.base_url}/chat/completions',
                json=payload,
                timeout=self.timeout
            )
            r.raise_for_status()
            text = r.json()['choices'][0]['message']['content']
            return _clean_response(text)
        except Exception as e:
            return None

    def _generate_raw(self, prompt: str) -> Optional[str]:
        """Send any prompt and return raw text — no room-description formatting."""
        try:
            r = requests.post(
                f'{self.base_url}/chat/completions',
                json={'model': self.model,
                      'messages': [{'role': 'user', 'content': prompt}],
                      'max_tokens': 1200, 'temperature': 0.7},
                timeout=self.timeout)
            r.raise_for_status()
            return r.json()['choices'][0]['message']['content'].strip()
        except Exception:
            return None


# ── Provider 2: Claude API ───────────────────────────────────

class ClaudeProvider(LLMProvider):
    """
    Uses Anthropic's Claude API for room description generation.
    Best quality output. Requires ANTHROPIC_API_KEY.
    Uses claude-haiku for speed and cost efficiency.
    """

    ANTHROPIC_API = 'https://api.anthropic.com/v1/messages'

    def __init__(self, api_key: str = '',
                 model: str = 'claude-haiku-4-5-20251001',
                 max_tokens: int = 500):
        self.api_key   = api_key
        self.model     = model
        self.max_tokens = max_tokens

    @property
    def name(self) -> str:
        return f'Claude API ({self.model})'

    def is_available(self) -> bool:
        return bool(self.api_key and self.api_key.startswith('sk-ant-'))

    def generate(self, world_name: str, room_name: str) -> Optional[str]:
        if not self.is_available():
            return None
        prompt = ROOM_PROMPT.format(world_name=world_name, room_name=room_name)
        try:
            headers = {
                'x-api-key':         self.api_key,
                'anthropic-version': '2023-06-01',
                'content-type':      'application/json',
            }
            payload = {
                'model':      self.model,
                'max_tokens': self.max_tokens,
                'messages':   [{'role': 'user', 'content': prompt}],
            }
            r = requests.post(self.ANTHROPIC_API, headers=headers,
                              json=payload, timeout=30)
            r.raise_for_status()
            text = r.json()['content'][0]['text']
            return _clean_response(text)
        except Exception:
            return None

    def _generate_raw(self, prompt: str) -> Optional[str]:
        """Send any prompt and return raw text."""
        if not self.is_available():
            return None
        try:
            r = requests.post(
                self.ANTHROPIC_API,
                headers={'x-api-key': self.api_key,
                         'anthropic-version': '2023-06-01',
                         'content-type': 'application/json'},
                json={'model': self.model, 'max_tokens': 1200,
                      'messages': [{'role': 'user', 'content': prompt}]},
                timeout=30)
            r.raise_for_status()
            return r.json()['content'][0]['text'].strip()
        except Exception:
            return None


# ── Provider 3: HuggingFace Inference API ───────────────────

class HuggingFaceProvider(LLMProvider):
    """
    Uses HuggingFace Inference API for text generation.
    Free tier available. Requires HF_API_KEY.
    
    Good models for game descriptions:
      - meta-llama/Meta-Llama-3-8B-Instruct
      - mistralai/Mistral-7B-Instruct-v0.3
      - microsoft/Phi-3-mini-4k-instruct
    """

    HF_API = 'https://api-inference.huggingface.co/models/{model}'

    def __init__(self, api_key: str = '',
                 model: str = 'meta-llama/Meta-Llama-3-8B-Instruct'):
        self.api_key = api_key
        self.model   = model

    @property
    def name(self) -> str:
        return f'HuggingFace ({self.model.split("/")[-1]})'

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key) > 10)

    def generate(self, world_name: str, room_name: str) -> Optional[str]:
        if not self.is_available():
            return None
        prompt = ROOM_PROMPT.format(world_name=world_name, room_name=room_name)
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            payload = {
                'inputs': prompt,
                'parameters': {
                    'max_new_tokens':  400,
                    'temperature':     0.8,
                    'return_full_text': False,
                }
            }
            url = self.HF_API.format(model=self.model)
            r = requests.post(url, headers=headers, json=payload, timeout=60)
            
            # HF returns 503 while model loads — retry once
            if r.status_code == 503:
                time.sleep(10)
                r = requests.post(url, headers=headers, json=payload, timeout=60)
            
            r.raise_for_status()
            data = r.json()
            
            if isinstance(data, list) and data:
                text = data[0].get('generated_text', '')
            elif isinstance(data, dict):
                text = data.get('generated_text', '')
            else:
                return None
                
            # HF sometimes returns the prompt + completion
            if prompt in text:
                text = text.replace(prompt, '').strip()
                
            return _clean_response(text) if text else None
        except Exception:
            return None

    def _generate_raw(self, prompt: str) -> Optional[str]:
        """Send any prompt and return raw text."""
        if not self.is_available():
            return None
        try:
            r = requests.post(
                self.HF_API.format(model=self.model),
                headers={'Authorization': f'Bearer {self.api_key}'},
                json={'inputs': prompt,
                      'parameters': {'max_new_tokens': 1200,
                                     'temperature': 0.7,
                                     'return_full_text': False}},
                timeout=60)
            r.raise_for_status()
            data = r.json()
            text = data[0].get('generated_text', '') if isinstance(data, list) else ''
            return text.replace(prompt, '').strip() if prompt in text else text
        except Exception:
            return None


# ── Provider 4: Template (always works) ──────────────────────

class TemplateProvider(LLMProvider):
    """
    Template-based fallback. Always available. Zero dependencies.
    Uses world theme + room name to select from curated templates.
    Better than nothing — produces coherent, thematic descriptions.
    """

    # Theme keywords → description style
    THEME_STYLES = {
        'barbie':    ('glamorous', 'pink and shimmering', 'fashion accessories'),
        'bewitched': ('magical', 'warm and cozy', 'hints of enchantment'),
        'mash':      ('austere', 'olive drab and worn', 'the sounds of the nearby front'),
        'area 51':   ('classified', 'sterile and humming', 'alien technology'),
        'hogan':     ('clandestine', 'rough-hewn wood', 'the distant sound of guards'),
        'zork':      ('ancient', 'stone and shadow', 'a faint adventurer\'s instinct'),
        'haunted':   ('foreboding', 'dark and cobwebbed', 'an unnatural chill'),
        'hogwarts':  ('magical', 'candlelit stone', 'the rustle of enchanted parchment'),
    }

    DEFAULT_STYLE = ('mysterious', 'atmospheric', 'a sense of possibility')

    @property
    def name(self) -> str:
        return 'Template (fallback)'

    def is_available(self) -> bool:
        return True  # Always available

    def _get_style(self, world_name: str):
        wl = world_name.lower()
        for key, style in self.THEME_STYLES.items():
            if key in wl:
                return style
        return self.DEFAULT_STYLE

    def generate(self, world_name: str, room_name: str) -> Optional[str]:
        adj, texture, detail = self._get_style(world_name)
        
        import random
        templates = [
            (f"The {room_name} carries the unmistakable character of {world_name}. "
             f"Everything here is {adj} in ways that are immediately apparent — "
             f"the {texture} surfaces, the quality of light, the {detail} that "
             f"fills the air. This is a space that knows what it is."),

            (f"You stand in the {room_name}. The atmosphere of {world_name} "
             f"is palpable here — {adj} and distinct. The {texture} surroundings "
             f"hold their secrets quietly, while {detail} reminds you exactly "
             f"where you are and what this place demands of you."),

            (f"The {room_name} of {world_name}. {adj.capitalize()} light plays "
             f"across {texture} surfaces, and the air carries {detail}. "
             f"It is a room that has seen things and remembers them, even if "
             f"it chooses not to share them immediately."),
        ]
        return random.choice(templates)

    def _generate_raw(self, prompt: str):
        """Template provider cannot answer freeform prompts."""
        return None


# ── Provider Chain Orchestrator ──────────────────────────────

class ProviderChain:
    """
    Tries each provider in order. First success wins.
    Logs which provider was used for each room.
    """

    def __init__(self, providers: list):
        self.providers = providers
        self._last_provider_used = None

    @property
    def last_provider(self) -> str:
        return self._last_provider_used or 'none'

    def detect(self) -> dict:
        """Check availability of all providers. Returns status dict."""
        status = {}
        for p in self.providers:
            available = p.is_available()
            status[p.name] = available
        return status

    def generate_raw(self, prompt: str) -> str:
        """
        Send any freeform prompt to the first available LLM provider.
        Used by: theme classifier, room namer, content enricher.
        TemplateProvider is skipped — it cannot answer freeform prompts.
        Returns empty string if no real LLM provider is available.
        """
        for provider in self.providers:
            if isinstance(provider, TemplateProvider):
                continue  # skip — template cannot answer freeform
            if not provider.is_available():
                continue
            result = provider._generate_raw(prompt)
            if result and len(result.strip()) > 5:
                self._last_provider_used = provider.name
                return result
        return ''

    def generate(self, world_name: str, room_name: str) -> str:
        """Try each provider in order. Returns description from first success."""
        for provider in self.providers:
            if not provider.is_available():
                continue
            result = provider.generate(world_name, room_name)
            if result and len(result.strip()) > 20:
                self._last_provider_used = provider.name
                return result
        
        # Should never reach here — TemplateProvider always succeeds
        self._last_provider_used = 'emergency_fallback'
        return f"The {room_name} of {world_name}. Exits lead onward."

    def detect_and_report(self) -> str:
        """Human-readable provider status for wizard display."""
        lines = ['\nInfinite Improbability Drive — Provider Status:',
                 '=' * 48]
        status = self.detect()
        first_available = None
        for name, available in status.items():
            icon = '✅' if available else '❌'
            lines.append(f'  {icon}  {name}')
            if available and not first_available:
                first_available = name
        lines.append('')
        lines.append(f'  Active provider: {first_available or "Template fallback"}')
        return '\n'.join(lines)


# ── Factory function ─────────────────────────────────────────

def build_provider_chain(config: dict) -> ProviderChain:
    """
    Build a ProviderChain from config dict.
    Config comes from improbability_drive.ini
    
    Example config:
    {
        'gpt4all_host': 'localhost',
        'gpt4all_port': '4891', 
        'gpt4all_model': 'Llama 3 8B Instruct',
        'claude_api_key': 'sk-ant-...',
        'huggingface_api_key': 'hf-...',
        'huggingface_model': 'meta-llama/Meta-Llama-3-8B-Instruct',
    }
    """
    providers = [
        GPT4AllProvider(
            host    = config.get('gpt4all_host', 'localhost'),
            port    = int(config.get('gpt4all_port', 4891)),
            model   = config.get('gpt4all_model', 'Llama 3 8B Instruct'),
            timeout = int(config.get('gpt4all_timeout', 60)),
        ),
        ClaudeProvider(
            api_key = config.get('claude_api_key', ''),
            model   = config.get('claude_model', 'claude-haiku-4-5-20251001'),
        ),
        HuggingFaceProvider(
            api_key = config.get('huggingface_api_key', ''),
            model   = config.get('huggingface_model',
                                 'meta-llama/Meta-Llama-3-8B-Instruct'),
        ),
        TemplateProvider(),  # Always last — always available
    ]
    return ProviderChain(providers)


# ── Quick test ───────────────────────────────────────────────

if __name__ == '__main__':
    print('Testing LLM Providers...\n')
    
    chain = build_provider_chain({
        'gpt4all_host': 'localhost',
        'gpt4all_port': '4891',
        'gpt4all_model': 'Llama 3 8B Instruct',
    })
    
    print(chain.detect_and_report())
    print()
    
    test_rooms = [
        ('Bewitched',   'Living Room'),
        ('Barbie World', 'Dream Kitchen'),
        ('Area 51',     'Hangar 18'),
        ('MASH 4077',   'Operating Room'),
    ]
    
    for world, room in test_rooms:
        print(f'Generating: {world} / {room}')
        desc = chain.generate(world, room)
        print(f'Provider:   {chain.last_provider}')
        print(f'Result:     {desc[:120]}...')
        print()
