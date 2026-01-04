// src/main/java/com/gifpt/workspace/service/WorkspaceService.java
package com.gifpt.workspace.service;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.AnalysisStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.security.auth.user.CustomUserPrincipal;
import com.gifpt.user.domain.User;
import com.gifpt.user.repository.UserRepository;
import com.gifpt.workspace.domain.Workspace;
import com.gifpt.workspace.dto.WorkspaceResponse;
import com.gifpt.workspace.dto.ChatResponse;
import com.gifpt.workspace.repository.WorkspaceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.client.RestClient;
import com.gifpt.file.domain.UploadFile;
import com.gifpt.file.repository.UploadedFileRepository;
import org.springframework.http.MediaType;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import lombok.extern.slf4j.Slf4j;

@Slf4j
@Service
@RequiredArgsConstructor
public class WorkspaceService {

    private final WorkspaceRepository workspaceRepository;
    private final AnalysisJobRepository analysisJobRepository;
    private final UserRepository userRepository;
    private final UploadedFileRepository uploadedFileRepository;
    private final WorkspaceChatAiClient workspaceChatAiClient;

    private final RestClient.Builder restClientBuilder;

    @Value("${gifpt.upload-dir}")
    private String uploadDir;

    @Value("${gifpt.ai-server.base-url}")
    private String aiServerBaseUrl; // 예: http://django:8000

    /**
     * 1) PDF 저장
     * 2) AnalysisJob 생성 + Django에 분석 요청
     * 3) Workspace 생성
     */
    @Transactional
    public WorkspaceResponse createWorkspace(
            CustomUserPrincipal principal,
            String title,
            String prompt,
            MultipartFile pdf
    ) throws IOException {
        long requestStart = System.currentTimeMillis();
        log.info("[REQUEST START] createWorkspace userId={}", principal.getId());

        User owner = userRepository.findById(principal.getId())
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        // 1) PDF 저장
        String storedPdfPath = storePdfFile(pdf);

        // 2) 분석 Job 생성 (DB)
        AnalysisJob job = AnalysisJob.builder()
                .status(AnalysisStatus.PENDING)
                .build();

        analysisJobRepository.save(job);

        // 2-1) RestClient 생성 (Builder 사용)
        RestClient restClient = restClientBuilder
                .baseUrl(aiServerBaseUrl)   // 예: http://django:8000
                .build();

        // Django /worker 쪽에 분석 요청
        var requestBody = java.util.Map.of(
                "job_id", job.getId(),
                "file_path", storedPdfPath,
                "prompt", prompt
        );

        restClient.post()
                .uri("/analyze")  // base-url + path
                .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                .body(requestBody)
                .retrieve()
                .toBodilessEntity();

        // 3) Workspace 생성
        Workspace workspace = Workspace.builder()
                .owner(owner)
                .title(title)
                .prompt(prompt)
                .pdfPath(storedPdfPath)
                .analysisJob(job)
                .status(Workspace.WorkspaceStatus.PENDING)
                .build();

        workspaceRepository.save(workspace);

        long requestEnd = System.currentTimeMillis();
        log.info(
                "[REQUEST END] createWorkspace workspaceId={} elapsed={}ms",
                workspace.getId(),
                (requestEnd - requestStart)
            );

        return toDto(workspace);
    }

    public WorkspaceResponse getWorkspace(Long workspaceId, Long userId) {
        long start = System.currentTimeMillis();

        Workspace ws = workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new IllegalArgumentException("Workspace not found"));

        if (!ws.getOwner().getId().equals(userId)) {
            throw new IllegalArgumentException("Forbidden workspace");
        }

        WorkspaceResponse resp = toDto(ws);

        long elapsed = System.currentTimeMillis() - start;
        log.info(
            "[WORKSPACE GET] workspaceId={} userId={} elapsed={}ms status={}",
            workspaceId,
            userId,
            elapsed,
            ws.getStatus()
        );
    
        return resp;
    }

    /**
     * Django에서 /api/v1/analysis/{jobId}/complete 콜백 들어올 때
     * AnalysisJobRepository에서 job 찾고, 연결된 Workspace도 함께 갱신
     */
    public void onAnalysisCompleted(
            Long jobId,
            String status,
            String summary,
            String resultUrl
    ) {
        AnalysisJob job = analysisJobRepository.findById(jobId)
                .orElseThrow(() -> new IllegalArgumentException("AnalysisJob not found"));

        // AnalysisJob 상태 갱신
        job.setStatus(AnalysisStatus.valueOf(status));
        job.setSummary(summary);
        job.setResultUrl(resultUrl);
        analysisJobRepository.save(job);

        // Workspace 찾기
        workspaceRepository.findByAnalysisJobId(jobId)
                .ifPresent(ws -> {
                    ws.setSummary(summary);
                    ws.setVideoUrl(resultUrl);
                    ws.setStatus(
                            "SUCCESS".equals(status)
                                    ? Workspace.WorkspaceStatus.SUCCESS
                                    : Workspace.WorkspaceStatus.FAILED
                    );
                    workspaceRepository.save(ws);

                    // 🔥 여기서 채팅봇 초기 메시지로 summary를 심어줄 수 있음
                    // e.g. workspaceChatService.addSystemMessage(ws, summary);
                });
    }

    private String storePdfFile(MultipartFile pdf) throws IOException {
        Path baseDir = Paths.get(uploadDir);
        Files.createDirectories(baseDir);

        String filename = System.currentTimeMillis() + "_" + pdf.getOriginalFilename();
        Path target = baseDir.resolve(filename);
        Files.copy(pdf.getInputStream(), target);

        return target.toString();
    }

    private WorkspaceResponse toDto(Workspace ws) {
        return new WorkspaceResponse(
                ws.getId(),
                ws.getTitle(),
                ws.getPrompt(),
                ws.getPdfPath(),
                ws.getSummary(),
                ws.getVideoUrl(),
                ws.getStatus(),
                ws.getCreatedAt(),
                ws.getUpdatedAt()
        );
    }

    public WorkspaceResponse createWorkspaceFromUploadedFile(
        CustomUserPrincipal principal,
        Long fileId,
        String title,
        String userPrompt
        ) throws IOException {

        // 1) 워크스페이스 owner 조회
        User owner = userRepository.findById(principal.getId())
                .orElseThrow(() -> new IllegalArgumentException("User not found"));

        // 2) 업로드된 파일 엔티티 조회
        UploadFile file = uploadedFileRepository.findById(fileId)
                .orElseThrow(() -> new IllegalArgumentException("파일을 찾을 수 없습니다. id=" + fileId));

        // 3) 분석 Job 생성
        AnalysisJob job = AnalysisJob.builder()
                .status(AnalysisStatus.PENDING)
                .build();
        analysisJobRepository.save(job);

        // 4) Django 워커에 분석 요청
        RestClient restClient = restClientBuilder
                .baseUrl(aiServerBaseUrl)   // 예: http://django:8000
                .build();

        var requestBody = java.util.Map.of(
                "job_id", job.getId(),
                // 🔥 UploadFile 엔티티의 경로 필드 이름에 맞게 수정해야 함
                "file_path", file.getS3Url(),      // 예: getPath(), getStoredPath() 등
                "prompt", userPrompt
        );

        log.info("🔥 [Spring→Django] POST {}/analyze body={}", aiServerBaseUrl, requestBody);

        restClient.post()
                .uri(uriBuilder -> uriBuilder
                        .path("/analyze")
                        .queryParam("job_id", job.getId())
                        .queryParam("file_path", file.getS3Url())
                        .queryParam("prompt", userPrompt)
                        .build())
                .accept(MediaType.APPLICATION_JSON)
                .retrieve()
                .toBodilessEntity();

        // 5) Workspace 생성
        Workspace workspace = Workspace.builder()
                .owner(owner)
                .title(title)
                .prompt(userPrompt)
                .pdfPath(file.getS3Url())
                .analysisJob(job)
                .status(Workspace.WorkspaceStatus.PENDING)
                .build();

        workspaceRepository.save(workspace);

        // 6) DTO로 변환해서 리턴
        return toDto(workspace);
        }

    /**
     * ✅ 내 워크스페이스 목록 조회 (페이징)
     */
    public Page<WorkspaceResponse> getMyWorkspaces(Long userId, Pageable pageable) {
        // ownerId 기준으로 워크스페이스 조회
        var page = workspaceRepository.findByOwnerId(userId, pageable);

        return page.map(this::toDto);
    }

    public ChatResponse chatOnWorkspace(Long userId, Long workspaceId, String message) {
        Workspace ws = workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new IllegalArgumentException("Workspace not found"));
    
        if (!ws.getOwner().getId().equals(userId)) {
            throw new IllegalArgumentException("Forbidden workspace");
        }
    
        // 요약/원래 프롬프트 가져오기
        String summary = ws.getSummary();       // 분석 결과 요약
        String userPrompt = ws.getPrompt();     // 처음에 사용자가 넣은 프롬프트
    
        if (summary == null) {
            // 아직 분석 안 끝난 경우
            throw new IllegalStateException("Analysis not completed yet for this workspace.");
        }
    
        // pdf 원문을 나중에 넣고 싶으면 여기서 조회해서 넘기면 됨
        String pdfText = null;
    
        String answer = workspaceChatAiClient.askWithContext(
                userPrompt,
                summary,
                pdfText,
                message
        );
    
        return new ChatResponse(answer);
    }

    @Transactional
    public void deleteWorkspace(Long workspaceId, Long userId) {
        Workspace ws = workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new IllegalArgumentException("Workspace not found"));

        // 🔒 소유자 체크
        if (!ws.getOwner().getId().equals(userId)) {
            throw new IllegalArgumentException("Forbidden workspace");
        }

        // TODO: 필요하면 여기서
        //  - 로컬/ S3에 저장된 PDF/영상 삭제
        //  - AnalysisJob도 같이 삭제(연관관계 cascade 설정 여부에 따라)
        // 같은 후처리를 넣을 수 있음

        workspaceRepository.delete(ws);
        log.info("🗑️ Workspace {} deleted by user {}", workspaceId, userId);
    }
}
