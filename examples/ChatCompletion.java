// A chat completion against Privatemode from plain Java, no dependencies.
//
//   java examples/ChatCompletion.java "Explain remote attestation in two sentences."
//
// Needs Java 17 or newer and the Privatemode proxy on localhost:8080 (make proxy).
// The proxy verifies the deployment and encrypts the prompt. This code only speaks
// the OpenAI-compatible chat completions API to localhost.
//
// With Spring AI or LangChain4j it is the same idea: keep your code, point the base URL
// of the OpenAI client at http://localhost:8080 and use a Privatemode model ID.

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

public class ChatCompletion {

    public static void main(String[] args) throws Exception {
        String base = System.getenv().getOrDefault("PRIVATEMODE_BASE_URL", "http://localhost:8080");
        String model = System.getenv().getOrDefault("PRIVATEMODE_MODEL", "glm-latest");
        String prompt = args.length > 0 ? args[0] : "Explain remote attestation in two sentences.";

        String body = """
            {"model": %s, "reasoning_effort": "low",
             "messages": [{"role": "user", "content": %s}]}
            """.formatted(quote(model), quote(prompt));

        HttpRequest request = HttpRequest.newBuilder(URI.create(base + "/v1/chat/completions"))
                .timeout(Duration.ofMinutes(2))
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(body))
                .build();

        HttpResponse<String> response = HttpClient.newHttpClient()
                .send(request, HttpResponse.BodyHandlers.ofString());

        if (response.statusCode() != 200) {
            System.err.println("HTTP " + response.statusCode() + ": " + response.body());
            System.exit(1);
        }
        System.out.println(firstContent(response.body()));
    }

    /** Minimal JSON string quoting, enough for a prompt. Use Jackson in real code. */
    static String quote(String s) {
        StringBuilder sb = new StringBuilder("\"");
        for (char c : s.toCharArray()) {
            switch (c) {
                case '"' -> sb.append("\\\"");
                case '\\' -> sb.append("\\\\");
                case '\n' -> sb.append("\\n");
                case '\r' -> sb.append("\\r");
                case '\t' -> sb.append("\\t");
                default -> sb.append(c < 0x20 ? String.format("\\u%04x", (int) c) : String.valueOf(c));
            }
        }
        return sb.append('"').toString();
    }

    /** Pulls choices[0].message.content out of the response without a JSON library. */
    static String firstContent(String json) {
        Matcher m = Pattern.compile("\"content\"\\s*:\\s*\"((?:[^\"\\\\]|\\\\.)*)\"").matcher(json);
        if (!m.find()) {
            return json;
        }
        String raw = m.group(1);
        StringBuilder out = new StringBuilder();
        for (int i = 0; i < raw.length(); i++) {
            char c = raw.charAt(i);
            if (c != '\\' || i + 1 >= raw.length()) {
                out.append(c);
                continue;
            }
            char n = raw.charAt(++i);
            switch (n) {
                case 'n' -> out.append('\n');
                case 't' -> out.append('\t');
                case 'r' -> out.append('\r');
                case 'u' -> {
                    out.append((char) Integer.parseInt(raw.substring(i + 1, i + 5), 16));
                    i += 4;
                }
                default -> out.append(n);
            }
        }
        return out.toString().strip();
    }
}
