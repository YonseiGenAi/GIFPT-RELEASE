// src/main/java/com/gifpt/analysis/controller/AnalysisCallbackController.java
package com.gifpt.analysis.controller;

import com.gifpt.analysis.dto.AnalysisCallbackDTO;
import com.gifpt.analysis.service.AnalysisJobService;
import com.gifpt.workspace.service.WorkspaceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/analysis")
@RequiredArgsConstructor
public class AnalysisCallbackController {

    private final AnalysisJobService analysisJobService;
    private final WorkspaceService workspaceService;

    @PostMapping("/{jobId}/complete")
    public ResponseEntity<Void> complete(
            @PathVariable Long jobId,
            @RequestBody AnalysisCallbackDTO dto
    ) {
        // 1) 기존 분석 Job 갱신
        analysisJobService.markCompleted(jobId, dto);

        // 2) Workspace에도 결과 반영 + 채팅봇 seed
        workspaceService.onAnalysisCompleted(
                jobId,
                dto.status().name(),   // PENDING / RUNNING / SUCCESS / FAILED
                dto.summary(),
                dto.resultUrl()
        );

        return ResponseEntity.ok().build();
    }
}
