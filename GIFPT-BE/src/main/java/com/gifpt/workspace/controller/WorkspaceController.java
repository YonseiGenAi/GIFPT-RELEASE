package com.gifpt.workspace.controller;

import com.gifpt.security.auth.user.CustomUserPrincipal;
import com.gifpt.workspace.dto.WorkspaceResponse;
import com.gifpt.workspace.service.WorkspaceService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

@RestController
@RequestMapping("/api/v1/workspaces")
@RequiredArgsConstructor
public class WorkspaceController {

    private final WorkspaceService workspaceService;

    /**
     * Create My Project 버튼 눌렀을 때 호출:
     * - multipart/form-data:
     *   - title: 문자열
     *   - prompt: 문자열
     *   - pdf: 파일
     */
    @PostMapping(consumes = {"multipart/form-data"})
    public ResponseEntity<WorkspaceResponse> createWorkspace(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @RequestPart("title") String title,
            @RequestPart("prompt") String prompt,
            @RequestPart("pdf") MultipartFile pdf
    ) throws Exception {
        WorkspaceResponse resp = workspaceService.createWorkspace(user, title, prompt, pdf);
        return ResponseEntity.ok(resp);
    }

    /**
     * 워크스페이스 상세 조회:
     *  - summary / videoUrl / 상태 / 타임스탬프 등 포함
     */
    @GetMapping("/{workspaceId}")
    public ResponseEntity<WorkspaceResponse> getWorkspace(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @PathVariable Long workspaceId
    ) {
        WorkspaceResponse resp = workspaceService.getWorkspace(workspaceId, user.getId());
        return ResponseEntity.ok(resp);
    }
}
