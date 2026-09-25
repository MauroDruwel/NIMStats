import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import test_models


class FakeResponse:
    status = 200

    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def __iter__(self):
        return iter(self.lines)


class TestModelRequests(unittest.TestCase):
    def run_call(self, model, lines):
        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["timeout"] = timeout
            return FakeResponse(lines)

        with patch("urllib.request.urlopen", fake_urlopen):
            result = test_models.call_model(model, "test prompt")
        return result, captured["payload"]

    def test_glm_models_use_low_effort_and_room_for_final_answer(self):
        lines = [
            b'data:{"choices":[{"delta":{"content":"answer"},"finish_reason":"stop"}]}\n',
            b"data:[DONE]\n",
        ]
        for model in test_models.GLM_THINKING_MODELS:
            with self.subTest(model=model):
                result, payload = self.run_call(model, lines)
                self.assertTrue(result["success"])
                self.assertEqual(payload["reasoning_effort"], "low")
                self.assertEqual(payload["max_tokens"], 2048)
                self.assertEqual(payload["temperature"], 0.7)
                self.assertEqual(payload["top_p"], 0.9)

    def test_other_models_keep_common_benchmark_parameters(self):
        lines = [
            b'data: {"choices":[{"delta":{"content":"answer"},"finish_reason":"stop"}]}\n',
            b"data: [DONE]\n",
        ]
        result, payload = self.run_call("nvidia/nemotron-3-super-120b-a12b", lines)
        self.assertTrue(result["success"])
        self.assertEqual(payload["max_tokens"], 500)
        self.assertNotIn("reasoning_effort", payload)

    def test_reasoning_only_stream_is_not_success_and_has_diagnostics(self):
        lines = [
            b'data: {"choices":[{"delta":{"reasoning_content":"thinking"},"finish_reason":null}]}\n',
            b'data: {"choices":[{"delta":{},"finish_reason":"length"}],"usage":{"completion_tokens":500}}\n',
            b"data: [DONE]\n",
        ]
        result, _payload = self.run_call("z-ai/glm-5.3-flash", lines)
        self.assertFalse(result["success"])
        self.assertIn(f"reasoning_chars={len('thinking')}", result["error"])
        self.assertIn("finish_reason=length", result["error"])


if __name__ == "__main__":
    unittest.main()
