package com.gifpt.workspace.controller;

import com.gifpt.security.auth.user.CustomUserPrincipal;
import com.gifpt.workspace.dto.WorkspaceResponse;
import com.gifpt.workspace.dto.WorkspaceCreateFromFileRequest;
import com.gifpt.workspace.service.WorkspaceService;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.web.PageableDefault;
import org.springframework.data.domain.Sort;
import org.springframework.http.ResponseEntity;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.http.MediaType;
import com.gifpt.workspace.dto.ChatRequest;
import com.gifpt.workspace.dto.ChatResponse;

@RestController
@RequestMapping("/api/v1/workspaces")
@RequiredArgsConstructor
public class WorkspaceController {

    private final WorkspaceService workspaceService;

    // ✅ 1) 기존: 프론트에서 바로 PDF 업로드하는 버전 (multipart/form-data)
    @PostMapping(consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public ResponseEntity<WorkspaceResponse> createWorkspaceWithPdf(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @RequestPart("title") String title,
            @RequestPart("prompt") String prompt,
            @RequestPart("pdf") MultipartFile pdf
    ) throws Exception {
        WorkspaceResponse resp = workspaceService.createWorkspace(user, title, prompt, pdf);
        return ResponseEntity.ok(resp);
    }

    /**
     * ✅ 3) 내 워크스페이스 목록 조회 (페이징)
     * GET /api/v1/workspaces?page=0&size=10
     */
    @GetMapping
    public ResponseEntity<Page<WorkspaceResponse>> getMyWorkspaces(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @PageableDefault(size = 10, sort = "createdAt", direction = Sort.Direction.DESC)
            Pageable pageable
    ) {
        Page<WorkspaceResponse> resp = workspaceService.getMyWorkspaces(user.getId(), pageable);
        return ResponseEntity.ok(resp);
    }

    // ✅ 2) 새로 추가: 이미 업로드된 fileId를 사용하는 JSON 버전
    @PostMapping(value = "/from-file", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<WorkspaceResponse> createWorkspaceFromUploadedFile(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @RequestBody WorkspaceCreateFromFileRequest request
    ) throws Exception {
        WorkspaceResponse resp = workspaceService.createWorkspaceFromUploadedFile(
                user,
                request.fileId(),
                request.title(),
                request.userPrompt()
        );
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

    // ✅ 4) 워크스페이스 기반 챗봇
    @PostMapping("/{workspaceId}/chat")
    public ResponseEntity<ChatResponse> chatOnWorkspace(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @PathVariable Long workspaceId,
            @RequestBody ChatRequest request
    ) {
        ChatResponse resp = workspaceService.chatOnWorkspace(
                user.getId(),
                workspaceId,
                request.message()
        );
        return ResponseEntity.ok(resp);
    }

    // ✅ 워크스페이스 삭제
    @DeleteMapping("/{workspaceId}")
    public ResponseEntity<Void> deleteWorkspace(
            @AuthenticationPrincipal CustomUserPrincipal user,
            @PathVariable Long workspaceId
    ) {
        workspaceService.deleteWorkspace(workspaceId, user.getId());
        return ResponseEntity.noContent().build(); // 204
    }
}
