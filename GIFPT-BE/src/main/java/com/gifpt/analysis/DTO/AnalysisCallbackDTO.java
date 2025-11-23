package com.gifpt.analysis.dto;

import com.gifpt.analysis.domain.AnalysisStatus;

public record AnalysisCallbackDTO(
    AnalysisStatus status,
    String resultUrl,
    String summary,
    String errorMessage
) {}
