package com.gifpt.workspace.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.List;
import java.util.Map;

@Component
public class WorkspaceChatAiClient {

    private final RestClient restClient;

    @Value("${openai.api.key}")
    private String openAiApiKey;

    @Value("${openai.model:gpt-4o}")
    private String model;

    // ⚠️ RestClient.Builder 를 주입받아서 우리가 직접 RestClient 생성
    public WorkspaceChatAiClient(RestClient.Builder builder) {
        // baseUrl은 외부 HTTPS를 직접 쓰니까 굳이 지정 안 함
        this.restClient = builder.build();
    }

    public String askWithContext(String userPrompt,
                                 String summary,
                                 String pdfText,
                                 String message) {

        String systemContent = """
                You are an algorithm tutor.
                - The user uploaded a PDF about some algorithm.
                - Below is the summary extracted for visualization:
                %s

                - The user originally asked this prompt for visualization:
                %s

                Use these as context and answer the student's question clearly and concisely.
                """.formatted(
                summary != null ? summary : "(no summary yet)",
                userPrompt != null ? userPrompt : "(no prompt)"
        );

        // 필요하다면 pdfText도 잘라서 messages에 추가할 수 있음

        var body = Map.of(
                "model", model,
                "messages", List.of(
                        Map.of("role", "system", "content", systemContent),
                        Map.of("role", "user", "content", message)
                )
        );

        var resp = restClient.post()
                .uri("https://api.openai.com/v1/chat/completions")
                .contentType(MediaType.APPLICATION_JSON)
                .header("Authorization", "Bearer " + openAiApiKey)
                .body(body)
                .retrieve()
                .body(Map.class);

        // 안전하게 파싱
        try {
            var choices = (List<Map<String, Object>>) resp.get("choices");
            if (choices != null && !choices.isEmpty()) {
                var msg = (Map<String, Object>) choices.get(0).get("message");
                return (String) msg.get("content");
            }
        } catch (Exception ignored) { }

        return "Sorry, I couldn't generate an answer.";
    }
}
