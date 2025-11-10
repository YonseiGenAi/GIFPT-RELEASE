package com.gifpt.file.controller;

import com.gifpt.file.domain.UploadFile;
import com.gifpt.file.repository.UploadedFileRepository;
import com.gifpt.user.domain.User;
import com.gifpt.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.Authentication;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.*;
import java.time.Instant;
import java.util.Map;

@RequiredArgsConstructor
@RestController
@RequestMapping("/api/v1/file")
public class FileUploadController {

  private final UploadedFileRepository repo;   // ⚠️ 엔티티명이 UploadFile이면, 레포도 이름/제네릭 맞춰라
  private final UserRepository userRepository;
  private final Path uploadDir = Paths.get("uploads");

  @SuppressWarnings("null")
  @PostMapping("/upload")
  public ResponseEntity<?> uploadFile(
      @RequestParam("file") MultipartFile file,
      @RequestParam("prompt") String prompt,
      Authentication auth  // ✅ 이걸로 받는다
  ) throws IOException {

    // 1) 로그인 사용자 찾기 (JWT의 sub가 email이어야 함)
    String email = auth.getName();
    User user = userRepository.findByEmail(email)
        .orElseThrow(() -> new RuntimeException("user not found: " + email));

    // 2) 파일 저장 (로컬)
    Files.createDirectories(uploadDir);
    String fileName = Instant.now().toEpochMilli() + "_" + file.getOriginalFilename();
    Path filePath = uploadDir.resolve(fileName);
    Files.copy(file.getInputStream(), filePath, StandardCopyOption.REPLACE_EXISTING);

    // 3) DB 저장 (영속 User를 반드시 넣어야 함)
    final UploadFile uploaded = UploadFile.builder()
        .user(user)
        .fileName(fileName)
        .s3Url(filePath.toString()) // 로컬 경로
        .prompt(prompt)
        .build();

    repo.save(uploaded);

    return ResponseEntity.ok(Map.of(
        "message", "uploaded successfully",
        "fileName", fileName,
        "path", filePath.toString()
    ));
  }
}
