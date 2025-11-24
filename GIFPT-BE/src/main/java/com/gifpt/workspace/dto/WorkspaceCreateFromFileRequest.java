package com.gifpt.workspace.dto;

public record WorkspaceCreateFromFileRequest(
    String title,
    Long fileId,
    String userPrompt
) {}
