package com.gifpt.workspace.dto;

import com.gifpt.workspace.domain.Workspace.WorkspaceStatus;

import java.time.OffsetDateTime;

public record WorkspaceResponse(
        Long id,
        String title,
        String prompt,
        String pdfPath,
        String summary,
        String videoUrl,
        WorkspaceStatus status,
        OffsetDateTime createdAt,
        OffsetDateTime updatedAt
) {}
