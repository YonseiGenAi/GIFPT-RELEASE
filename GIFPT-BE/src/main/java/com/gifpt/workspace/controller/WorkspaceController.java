package com.gifpt.workspace.controller;

import com.gifpt.security.auth.user.CustomUserPrincipal;
import com.gifpt.workspace.dto.*;
import com.gifpt.workspace.service.WorkspaceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/workspace")
@RequiredArgsConstructor
public class WorkspaceController {

    private final WorkspaceService workspaceService;

    /**
     * ✅ 1) PDF + Prompt 업로드 → AnalysisJob 생성
     */
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<WorkspaceCreateResponseDTO> createWorkspace(
            @RequestPart("file") MultipartFile file,
            @RequestPart("prompt") String prompt,
            @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        WorkspaceCreateResponseDTO resp = workspaceService.createWorkspace(file, prompt, user.getId());
        return ResponseEntity.ok(resp);
    }

    /**
     * ✅ 2) Job 상태/요약/결과 조회 (프론트가 폴링)
     */
    @GetMapping("/{jobId}")
    public ResponseEntity<WorkspaceStatusResponseDTO> getWorkspace(
            @PathVariable Long jobId,
            @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        WorkspaceStatusResponseDTO resp = workspaceService.getWorkspace(jobId, user.getId());
        return ResponseEntity.ok(resp);
    }

    /**
     * ✅ 3) Chat with AI – PDF/요약/프롬프트 기반 질의응답
     */
    @PostMapping("/{jobId}/chat")
    public ResponseEntity<ChatResponse> chat(
            @PathVariable Long jobId,
            @RequestBody ChatRequest req,
            @AuthenticationPrincipal CustomUserPrincipal user
    ) {
        String answer = workspaceService.chat(jobId, user.getId(), req.getMessage());
        return ResponseEntity.ok(new ChatResponse(answer));
    }
}
