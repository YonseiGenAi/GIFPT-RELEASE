package com.gifpt.file.service;

import com.gifpt.file.domain.UploadFile;
import com.gifpt.file.repository.UploadedFileRepository;
import com.gifpt.user.domain.User;
import com.gifpt.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.time.Instant;

@Service
@RequiredArgsConstructor
public class UploadedFileService {

    private final UploadedFileRepository uploadedFileRepository;
    private final UserRepository userRepository;
    private final Path uploadDir = Paths.get("uploads");

    public UploadFile store(MultipartFile file, Long userId) {
        try {
            // 1) 사용자 조회
            User user = userRepository.findById(userId)
                    .orElseThrow(() -> new RuntimeException("User not found: " + userId));

            // 2) 파일 저장 (로컬)
            Files.createDirectories(uploadDir);
            String fileName = Instant.now().toEpochMilli() + "_" + file.getOriginalFilename();
            Path filePath = uploadDir.resolve(fileName);
            Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

            // 3) DB 저장
            UploadFile uploaded = UploadFile.builder()
                    .user(user)
                    .fileName(fileName)
                    .s3Url(filePath.toString()) // 로컬 경로
                    .build();

            return uploadedFileRepository.save(uploaded);
        } catch (IOException e) {
            throw new RuntimeException("Failed to store file", e);
        }
    }
}


