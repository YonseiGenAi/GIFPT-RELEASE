package com.gifpt.workspace.service;

import com.gifpt.analysis.domain.AnalysisJob;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
@RequiredArgsConstructor
public class WorkspaceAiClient {

    private final RestClient restClient;

    @Value("${gifpt.ai.base-url:http://django:8000}")
    private String aiBaseUrl;

    public void requestAnalysis(AnalysisJob job) {
        // Django 쪽에서 기대하는 payload 형식에 맞게 작성
        var body = new java.util.HashMap<String, Object>();
        body.put("jobId", job.getId());
        body.put("filePath", job.getUploadedFile().getS3Url());
        body.put("prompt", job.getPrompt());

        restClient.post()
                .uri(aiBaseUrl + "/studio/analyze")  // 예시
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .toBodilessEntity();
    }
}
