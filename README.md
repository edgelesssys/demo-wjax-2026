# demo-wjax-2026

Demo material for the talk "Ende-zu-Ende verschlüsselte KI per API" at W-JAX 2026 (3 to 5 November).

The scenario: a coding agent works on a data warehouse that contains personal data. The agent
is Claude Code or OpenCode, the model runs on [Privatemode](https://privatemode.ai), and the
warehouse is synthetic. The point of the demo is that the harness stays the same and only the
backend changes.

```
Claude Code / OpenCode  ->  Privatemode proxy (your machine)  ->  Privatemode API
   plain HTTP, localhost       verifies attestation,                confidential VM + GPU,
                               encrypts prompts                     memory stays encrypted
```

Everything in the warehouse is made up: names, e-mail addresses (`.test` is a reserved TLD),
phone numbers, support tickets. It is shaped like real shop data on purpose.

## Get an API key

The demo needs a Privatemode API key. Signing up and creating one takes a few minutes.

1. Open the [Privatemode portal](https://portal.privatemode.ai) and sign in, or
   [sign up](https://portal.privatemode.ai/sign-in/create).
2. Create an organization or select an existing one. Rate limits, usage, and billing are managed per organization.
3. Open **API keys** and create a new key. Give it a name. A comment, an expiration date, and custom limits are optional;
   without custom limits the organization defaults apply.
4. Copy the key right away and store it safely. Anyone who has it can use Privatemode at your cost.
5. Save it for this repo with `make key`. The prompt does not echo the key, and the file `.privatemode-api-key`
   is gitignored.

New organizations get a one-time quota of 5,000,000 tokens. After that, the free tier applies, with monthly limits that the
docs list under [rate limits](https://docs.privatemode.ai/rate-limits/). Check the **Usage** page in the portal after a
demo run to see what it cost. The full walkthrough is in the
[API quickstart](https://docs.privatemode.ai/getting-started/api/) and the
[API keys](https://docs.privatemode.ai/portal/api-keys/) docs.

## Quickstart

You need Docker, Python 3.10+, and the API key from above.

```bash
# 1. synthetic warehouse (about 1 second, writes data/warehouse.duckdb read-only)
make data

# 2. API key into a file, so it stays out of `ps`, `docker inspect`, and your shell history
make key

# 3. proxy on localhost:8080 (keep this terminal open)
make proxy

# 4. in a second terminal: is everything reachable?
make check

# or steps 3 and 4 in one command, with the proxy in the background:
make up          # stop it with `make down`, show its log with `make logs`

# 5. start an agent
make claude      # Claude Code, needs v2.1.242 or newer
make opencode    # OpenCode
```

A first prompt to try:

> Conversion in the shop dropped this week. Find out why. Use the warehouse, show me the numbers,
> and write a short summary with a recommendation to `analysis/summary.md`.

`make claude` writes `.claude/settings.local.json` in this directory (gitignored), so only
sessions started here use Privatemode. `rm .claude/settings.local.json` reverts it.

## Configuration

Both configurations follow the Privatemode docs for coding assistants:
[Claude Code](https://docs.privatemode.ai/cookbook/coding-assistants-claude-code/) and
[OpenCode](https://docs.privatemode.ai/cookbook/coding-assistants-opencode/).

| Tool | Config | Model |
| --- | --- | --- |
| Claude Code | `config/claude-code.settings.json` | `glm-latest`, alternative `glm-flash-latest` |
| OpenCode | `opencode.json` | `privatemode-ai/glm-latest` |

Any other tool that speaks the OpenAI or Anthropic API can use the proxy as well: base URL
`http://localhost:8080` (Anthropic-style) or `http://localhost:8080/v1` (OpenAI-style), any
placeholder as API key, the proxy adds the real one. Only Claude Code and OpenCode are covered
by the Privatemode docs; for other harnesses, try it before you put it on a slide.

The proxy image is pinned to `v1.60.0` in `scripts/proxy.sh`. Flag names changed between releases
(`--apiKey` became `--api-key`), and a cached `:latest` on your machine can be old. Check what you
run with `docker run --rm <image> --version`.

## Without an agent

`examples/ChatCompletion.java` is a chat completion in plain Java 17, no dependencies:

```bash
java examples/ChatCompletion.java "Explain remote attestation in two sentences."
```

`examples/curl.sh` does the same with curl.

`examples/spring-ai/` is a minimal Spring AI app (JDK 17+ and Maven). Plain Spring AI, nothing in the
code knows about Privatemode; three properties point it at the proxy:

```properties
spring.ai.openai.base-url=http://localhost:8080/v1
spring.ai.openai.api-key=placeholder
spring.ai.openai.chat.model=glm-latest
```

```bash
cd examples/spring-ai && mvn spring-boot:run
```

Tested with Spring AI 2.0.2 and Spring Boot 4.0.9 against proxy `v1.60.0`. Notes: the base URL
includes `/v1` (Spring AI 2 uses the official OpenAI Java SDK), and `api-key` must be set to
something, because Spring AI refuses to start without one. The proxy holds the real key, so a
placeholder is enough. The same applies to LangChain4j and other OpenAI-compatible clients: keep your
code, point the base URL at the proxy, use a Privatemode model ID.

## What is protected, and what is not

Protected by design: prompts and responses between your machine and the confidential environment
that runs the model. The proxy verifies the attestation of the deployment before it sends data,
and encrypts prompts before they leave your machine. The infrastructure provider and Edgeless
Systems have no access to them. See the Privatemode docs on
[security](https://docs.privatemode.ai/security/) and
[remote attestation](https://docs.privatemode.ai/security/attestation/overview/).

Not covered by that, and still your job:

- **The agent.** It runs on your machine with your permissions. Free text in your data, such as the
  support tickets in this warehouse, can contain instructions aimed at the agent (prompt injection).
- **Tool access.** The settings in this repo deny web access, `curl` and `wget`, and the database
  file is read-only. That is defense in depth, not a sandbox. For real data, run the agent in a
  container or VM that can reach nothing but the proxy.
- **Metadata.** The Privatemode FAQ lists what is stored for up to 90 days: IP, timestamp, API key,
  token usage, request path and status. Prompts and responses are not part of it.
- **Hardware.** Attacks on confidential computing hardware exist. Privatemode keeps a public
  [status page](https://docs.privatemode.ai/security/hw-integrity/) with mitigations, and the
  client verifies the patch level through attestation.
- **Debug flags.** Do not start the proxy with `--dump-requests`. It writes prompts to disk in plaintext.

## Layout

| Path | What |
| --- | --- |
| `data/generate.py` | builds the synthetic warehouse, deterministic with `--seed` |
| `AGENTS.md`, `CLAUDE.md` | project instructions the agents read |
| `config/`, `opencode.json` | agent configuration |
| `scripts/` | proxy launcher and pre-flight check |
| `examples/` | Java, Spring AI, and curl |
| `DEMO.md` | speaker runbook (German) |
