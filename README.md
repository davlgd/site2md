# site2md

Convert any website to Markdown or structured JSON. An ideal solution to provide content to LLMs(.txt). This project uses FastAPI and Trafilatura. It serves a simple API with optional KV (Materia, Redis, Valkey) caching and rate limiting.

## Usage

See the [example](https://github.com/davlgd/site2md/tree/main/example) directory to get started.

## Development & Tests

Install optional dependencies and run `pytest` to run the tests. If a KV local server is not running, corresponding tests will be skipped.

## License

This project is licensed under the terms of the MIT license. See the [LICENSE](https://github.com/davlgd/site2md/tree/main/LICENSE) file.