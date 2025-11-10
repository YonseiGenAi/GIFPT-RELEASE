package com.gifpt.analysis.DTO;

import com.gifpt.analysis.domain.JobStatus;

public record AnalysisCallbackDTO(
    JobStatus status,
    String resultUrl,
    String summary,
    String errorMessage
) {}
