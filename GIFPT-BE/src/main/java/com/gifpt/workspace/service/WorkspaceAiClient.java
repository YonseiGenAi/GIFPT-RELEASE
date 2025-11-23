package com.gifpt.workspace.service;

import com.gifpt.analysis.domain.AnalysisJob;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.util.HashMap;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class WorkspaceAiClient {

    private final RestClient restClient;

    public WorkspaceAiClient(
            RestClient.Builder builder,
            @Value("${gifpt.ai.base-url:http://django:8000}") String aiBaseUrl
    ) {
        this.restClient = builder
                .baseUrl(aiBaseUrl)
                .build();
    }

    public void requestAnalysis(AnalysisJob job) {
        Map<String, Object> body = new HashMap<>();
        body.put("jobId", job.getId());
        body.put("filePath", job.getUploadedFile().getS3Url());
        body.put("prompt", job.getPrompt());

        restClient.post()
                .uri("/studio/analyze")   // baseUrl + 이 path
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .toBodilessEntity();
    }
}
