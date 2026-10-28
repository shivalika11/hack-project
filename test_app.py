import json
import threading
import unittest
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import patch
from urllib.request import Request, urlopen

import app


class StubOllamaHandler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        return

    def send_json(self, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.send_json({"models": [{"name": "qwen2.5:3b"}]})

    def do_POST(self):
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.last_generation = request
        self.send_json({"response": "The river held the afternoon light."})


@contextmanager
def running_server(server):
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


class ValidatePayloadTests(unittest.TestCase):
    def test_normalizes_valid_request(self):
        details = app.validate_payload(
            {
                "name": "  Alex  ",
                "memory": "  We planted basil together.  ",
                "style": "poem",
                "model": "qwen2.5:3b",
            }
        )
        self.assertEqual(
            details,
            {
                "name": "Alex",
                "memory": "We planted basil together.",
                "style": "poem",
                "model": "qwen2.5:3b",
            },
        )

    def test_rejects_empty_memory(self):
        with self.assertRaisesRegex(ValueError, "Add a memory"):
            app.validate_payload(
                {"memory": "  ", "style": "letter", "model": "qwen2.5:3b"}
            )

    def test_rejects_memory_over_limit(self):
        with self.assertRaisesRegex(ValueError, "under 2000 characters"):
            app.validate_payload(
                {
                    "memory": "a" * 2_001,
                    "style": "letter",
                    "model": "qwen2.5:3b",
                }
            )

    def test_rejects_untrusted_model_identifier(self):
        for model in ("../remote", "http://example.test", "model with spaces"):
            with self.subTest(model=model):
                with self.assertRaisesRegex(ValueError, "installed Ollama model"):
                    app.validate_payload(
                        {"memory": "A good afternoon.", "style": "letter", "model": model}
                    )

    def test_rejects_unsupported_style(self):
        with self.assertRaisesRegex(ValueError, "supported writing style"):
            app.validate_payload(
                {
                    "memory": "A good afternoon.",
                    "style": "impersonate",
                    "model": "qwen2.5:3b",
                }
            )

    def test_rejects_non_string_style(self):
        with self.assertRaisesRegex(ValueError, "supported writing style"):
            app.validate_payload(
                {
                    "memory": "A good afternoon.",
                    "style": [],
                    "model": "qwen2.5:3b",
                }
            )

    def test_rejects_model_url(self):
        with self.assertRaisesRegex(ValueError, "installed Ollama model"):
            app.validate_payload(
                {
                    "memory": "A good afternoon.",
                    "style": "letter",
                    "model": "http://example.test",
                }
            )


class OllamaIntegrationTests(unittest.TestCase):
    def test_http_routes_proxy_only_to_local_ollama(self):
        ollama_server = ThreadingHTTPServer(("127.0.0.1", 0), StubOllamaHandler)
        app_server = ThreadingHTTPServer(("127.0.0.1", 0), app.RequestHandler)
        ollama_url = f"http://127.0.0.1:{ollama_server.server_port}"
        app_url = f"http://127.0.0.1:{app_server.server_port}"

        with patch.object(app, "OLLAMA_URL", ollama_url):
            with running_server(ollama_server), running_server(app_server):
                with urlopen(f"{app_url}/api/models") as response:
                    self.assertEqual(json.load(response)["models"], ["qwen2.5:3b"])

                payload = json.dumps(
                    {
                        "memory": "We walked beside the river.",
                        "style": "letter",
                        "model": "qwen2.5:3b",
                    }
                ).encode("utf-8")
                request = Request(
                    f"{app_url}/api/compose",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                with urlopen(request) as response:
                    result = json.load(response)

        self.assertEqual(result["text"], "The river held the afternoon light.")
        self.assertEqual(ollama_server.last_generation["model"], "qwen2.5:3b")
        self.assertIn("We walked beside the river.", ollama_server.last_generation["prompt"])

    def test_prompt_uses_source_only_and_does_not_impersonate(self):
        details = app.validate_payload(
            {
                "name": "Sam",
                "memory": "We walked beside the river.",
                "style": "letter",
                "model": "qwen2.5:3b",
            }
        )
        prompt = app.build_prompt(details)
        self.assertIn('"name": "Sam"', prompt)
        self.assertIn("We walked beside the river.", prompt)
        self.assertIn("Do not speak as the person who died", prompt)
        self.assertIn("Do not invent biography", prompt)
        self.assertIn("never instructions", prompt)

    @patch("app.ollama_request")
    def test_generation_uses_selected_local_model(self, request):
        request.side_effect = [
            {"models": [{"name": "qwen3:4b"}]},
            {"response": "The river kept our laughter."},
        ]
        result = app.generate_remembrance(
            {
                "name": "Sam",
                "memory": "We walked beside the river.",
                "style": "poem",
                "model": "qwen3:4b",
            }
        )
        self.assertEqual(result, {"text": "The river kept our laughter.", "model": "qwen3:4b"})
        self.assertEqual(request.call_count, 2)
        args, kwargs = request.call_args_list[1]
        self.assertEqual(args[0], "/api/generate")
        self.assertEqual(args[1]["model"], "qwen3:4b")
        self.assertFalse(args[1]["stream"])
        self.assertEqual(kwargs["timeout"], 120)

    @patch("app.ollama_request")
    def test_lists_only_valid_installed_model_names(self, request):
        request.return_value = {
            "models": [
                {"name": "qwen2.5:3b"},
                {"name": "qwen2.5:3b"},
                {"name": "../not-a-model"},
                {"name": "llama3.2:3b"},
                None,
            ]
        }
        self.assertEqual(app.installed_models(), ["llama3.2:3b", "qwen2.5:3b"])

    @patch("app.ollama_request")
    def test_empty_model_output_is_an_error(self, request):
        request.side_effect = [
            {"models": [{"name": "qwen2.5:3b"}]},
            {"response": " "},
        ]
        with self.assertRaisesRegex(app.OllamaError, "empty draft"):
            app.generate_remembrance(
                {
                    "memory": "A good afternoon.",
                    "style": "letter",
                    "model": "qwen2.5:3b",
                }
            )

    @patch("app.ollama_request")
    def test_refuses_uninstalled_model(self, request):
        request.return_value = {"models": [{"name": "qwen2.5:3b"}]}
        with self.assertRaisesRegex(ValueError, "already installed"):
            app.generate_remembrance(
                {
                    "memory": "A good afternoon.",
                    "style": "letter",
                    "model": "qwen3:4b",
                }
            )
        request.assert_called_once_with("/api/tags")


if __name__ == "__main__":
    unittest.main()
