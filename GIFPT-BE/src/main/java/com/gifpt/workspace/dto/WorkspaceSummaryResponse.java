package com.gifpt.workspace.dto;

import com.gifpt.workspace.domain.Workspace;
import java.time.LocalDateTime;

public record WorkspaceSummaryResponse(
        Long id,
        String title,
        Workspace.WorkspaceStatus status,
        String summary,
        String videoUrl,
        LocalDateTime createdAt,
        LocalDateTime updatedAt
) {
}
