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
import com.gifpt.workspace.repository.WorkspaceRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.client.RestClient;
import com.gifpt.file.domain.UploadFile;
import com.gifpt.file.repository.UploadedFileRepository;


import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

@Service
@RequiredArgsConstructor
public class WorkspaceService {

    private final WorkspaceRepository workspaceRepository;
    private final AnalysisJobRepository analysisJobRepository;
    private final UserRepository userRepository;
    private final UploadedFileRepository uploadedFileRepository;

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
    public WorkspaceResponse createWorkspace(
            CustomUserPrincipal principal,
            String title,
            String prompt,
            MultipartFile pdf
    ) throws IOException {

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
                "jobId", job.getId(),
                "inputPath", storedPdfPath,
                "prompt", prompt
        );

        restClient.post()
                .uri("/api/worker/analyze")  // base-url + path
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

        return toDto(workspace);
    }

    public WorkspaceResponse getWorkspace(Long workspaceId, Long userId) {
        Workspace ws = workspaceRepository.findById(workspaceId)
                .orElseThrow(() -> new IllegalArgumentException("Workspace not found"));

        if (!ws.getOwner().getId().equals(userId)) {
            throw new IllegalArgumentException("Forbidden workspace");
        }

        return toDto(ws);
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
                "jobId", job.getId(),
                // 🔥 UploadFile 엔티티의 경로 필드 이름에 맞게 수정해야 함
                "inputPath", file.getS3Url(),      // 예: getPath(), getStoredPath() 등
                "prompt", userPrompt
        );

        restClient.post()
                .uri("/api/worker/analyze")
                .body(requestBody)
                .retrieve()
                .toBodilessEntity();

        // 5) Workspace 생성
        Workspace workspace = Workspace.builder()
                .owner(owner)
                .title(title)
                .prompt(userPrompt)
                .pdfPath(file.getS3Url())          // 위와 동일하게 경로 필드 맞춰 줄 것
                .analysisJob(job)
                .status(Workspace.WorkspaceStatus.PENDING)
                .build();

        workspaceRepository.save(workspace);

        // 6) DTO로 변환해서 리턴
        return toDto(workspace);
        }
}
