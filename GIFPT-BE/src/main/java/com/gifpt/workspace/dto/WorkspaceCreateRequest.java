package com.gifpt.workspace.dto;

import org.springframework.web.multipart.MultipartFile;

public record WorkspaceCreateRequest(
        String title,
        String prompt,
        MultipartFile pdf
) {}
