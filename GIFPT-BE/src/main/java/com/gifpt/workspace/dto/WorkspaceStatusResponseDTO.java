package com.gifpt.workspace.dto;

import com.gifpt.analysis.domain.JobStatus;
import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class WorkspaceStatusResponseDTO {
    private Long jobId;
    private JobStatus status;
    private String summary;    // 요약 (완료 후)
    private String resultUrl;  // 영상 URL (완료 후)
}
