package demo;

import org.springframework.ai.chat.client.ChatClient;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    // Nothing here knows about Privatemode: this is plain Spring AI with the OpenAI client.
    @Bean
    CommandLineRunner ask(ChatClient.Builder chat) {
        return args -> System.out.println(chat.build()
                .prompt("Nenne drei Vorteile von verschlüsseltem Arbeitsspeicher. Kurz.")
                .call()
                .content());
    }
}
