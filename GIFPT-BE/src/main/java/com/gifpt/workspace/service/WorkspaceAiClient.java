// src/main/java/com/gifpt/workspace/service/WorkspaceAiClient.java
package com.gifpt.workspace.service;

import com.gifpt.analysis.domain.AnalysisJob;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.HashMap;
import java.util.Map;

@Component
public class WorkspaceAiClient {

    private final RestClient.Builder restClientBuilder;

    @Value("${gifpt.ai-server.base-url}")
    private String aiBaseUrl;

    // ✅ 생성자 하나만: Builder 주입
    public WorkspaceAiClient(RestClient.Builder restClientBuilder) {
        this.restClientBuilder = restClientBuilder;
    }

    public void requestAnalysis(AnalysisJob job) {
        // 요청 시점에 RestClient 생성
        RestClient restClient = restClientBuilder
                .baseUrl(aiBaseUrl)
                .build();

        Map<String, Object> body = new HashMap<>();
        body.put("job_id", job.getId());
        body.put("file_path", job.getUploadedFile().getS3Url());
        body.put("prompt", job.getPrompt());

        restClient.post()
                .uri("/analyze")   // baseUrl + 이 path
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .toBodilessEntity();
    }
}