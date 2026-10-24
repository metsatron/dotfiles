#!/usr/bin/env python3
"""Offline Mistral Pi output-budget and literate-source regression checks."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import unittest

ROOT = Path(os.environ.get('MISTRAL_PI_TEST_ROOT', Path(__file__).resolve().parents[5]))
MODELS = ROOT / 'all/.local/share/mistral-pi/models.json'
SETTINGS = ROOT / 'all/.local/share/mistral-pi/settings.json'


class MistralPiBudgetTest(unittest.TestCase):
    def test_large_has_explicit_response_budget(self):
        provider = json.loads(MODELS.read_text())['providers']['mistral']
        large = next(m for m in provider['models'] if m['id'] == 'mistral-large-4')
        self.assertEqual(large.get('maxTokens'), 32768,
                         'omission silently selects Pi custom-model default 16384')
        self.assertLess(large['maxTokens'], large['contextWindow'])
        self.assertFalse(large['reasoning'])
        self.assertEqual(provider['apiKey'], '$MISTRAL_API_KEY')
        self.assertEqual(json.loads(SETTINGS.read_text())['defaultModel'], 'mistral-large-4')

    def test_org_and_models_output_agree(self):
        source = (ROOT / 'tools-pi.org').read_text()
        match = re.search(r'^#\+BEGIN_SRC json :tangle all/\.local/share/mistral-pi/models\.json[^\n]*\n(.*?)^#\+END_SRC',
                          source, re.M | re.S)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), MODELS.read_text())

    def test_installed_pi_resolves_and_propagates_budget(self):
        root = Path(os.environ.get('MISTRAL_PI_PACKAGE',
                        Path.home()/'.npm-global/lib/node_modules/@earendil-works/pi-coding-agent'))
        if not (root/'dist/core/provider-composer.js').exists():
            self.skipTest('installed Pi integration fixture requires declared Pi package')
        node = shutil.which('node')
        if not node:
            self.skipTest('installed Pi integration fixture requires Node')
        config_url = (root/'dist/core/model-config.js').as_uri()
        composer_url = (root/'dist/core/provider-composer.js').as_uri()
        options_url = (root/'node_modules/@earendil-works/pi-ai/dist/api/simple-options.js').as_uri()
        script = f'''
import {{ModelConfig}} from {json.dumps(config_url)};
import {{composeModelProvider}} from {json.dumps(composer_url)};
import {{buildBaseOptions}} from {json.dumps(options_url)};
const c = await ModelConfig.load({json.dumps(str(MODELS))});
const p = composeModelProvider('mistral', undefined, c, undefined);
const m = p.getModels().find(m => m.id === 'mistral-large-4');
const options = buildBaseOptions(m, {{messages: []}}, {{}}, 'fixture-not-a-credential');
console.log(JSON.stringify({{modelBudget:m.maxTokens, requestBudget:options.maxTokens}}));
'''
        result = subprocess.run([node, '--input-type=module', '-e', script],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout),
                         {'modelBudget': 32768, 'requestBudget': 32768})


if __name__ == '__main__':
    unittest.main()
