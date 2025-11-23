package com.gifpt.workspace.service;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.analysis.domain.JobStatus;
import com.gifpt.analysis.repository.AnalysisJobRepository;
import com.gifpt.file.domain.UploadFile;
import com.gifpt.file.service.UploadedFileService;
import com.gifpt.workspace.dto.WorkspaceCreateResponseDTO;
import com.gifpt.workspace.dto.WorkspaceStatusResponseDTO;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

@Service
@RequiredArgsConstructor
public class WorkspaceService {

    private final UploadedFileService uploadedFileService;
    private final AnalysisJobRepository analysisJobRepository;
    private final WorkspaceAiClient workspaceAiClient; // 장고/오픈AI 호출용
    private final WorkspaceChatAiClient chatAiClient;  // Chat 전용

    /**
     * PDF + prompt 받아서 Job 생성 + Django worker 트리거
     */
    public WorkspaceCreateResponseDTO createWorkspace(
            MultipartFile file,
            String prompt,
            Long userId
    ) {
        // 1) 파일 저장
        UploadFile uploaded = uploadedFileService.store(file, userId);

        // 2) Job 생성
        AnalysisJob job = new AnalysisJob();
        job.setUserId(userId);
        job.setUploadedFile(uploaded);
        job.setPrompt(prompt);
        job.setStatus(JobStatus.PENDING);
        analysisJobRepository.save(job);

        // 3) Django worker(or Celery)에 작업 요청
        workspaceAiClient.requestAnalysis(job);

        return new WorkspaceCreateResponseDTO(job.getId());
    }

    /**
     * Job 상태 + 요약/결과 조회
     */
    public WorkspaceStatusResponseDTO getWorkspace(Long jobId, Long userId) {
        AnalysisJob job = analysisJobRepository
                .findByIdAndUserId(jobId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Job not found"));

        return WorkspaceStatusResponseDTO.builder()
                .jobId(job.getId())
                .status(job.getStatus())
                .summary(job.getSummary())
                .resultUrl(job.getResultUrl())
                .build();
    }

    /**
     * Chat with AI – 저장된 summary/prompt/pdf를 context로 사용
     */
    public String chat(Long jobId, Long userId, String message) {
        AnalysisJob job = analysisJobRepository
                .findByIdAndUserId(jobId, userId)
                .orElseThrow(() -> new IllegalArgumentException("Job not found"));

        // summary, prompt, pdf 텍스트를 context로 전달
        return chatAiClient.askWithContext(
                job.getPrompt(),
                job.getSummary(),
                job.getPdfText(),   // pdfText 필드를 AnalysisJob이나 UploadFile 쪽에 추가해두면 좋음
                message
        );
    }
}
