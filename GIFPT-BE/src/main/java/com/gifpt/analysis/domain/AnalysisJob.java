package com.gifpt.analysis.domain;

import com.gifpt.user.domain.User;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Getter @Setter
@NoArgsConstructor @AllArgsConstructor @Builder
@Table(name = "analysis_jobs")
public class AnalysisJob {

  @Id @GeneratedValue(strategy = GenerationType.IDENTITY)
  private Long id;

  @ManyToOne(fetch = FetchType.LAZY) // 선택: 누가 올렸는지
  @JoinColumn(name = "user_id")
  private User user;

  @Column(nullable = false)
  private String fileName;         // 업로드된 원본 파일명

  @Column(nullable = false)
  private String filePath;         // 로컬 경로나 S3 URL
  
  @Builder.Default
  @Enumerated(EnumType.STRING)
  @Column(nullable = false)
  private JobStatus status = JobStatus.PENDING;

  private String resultUrl;        // 생성된 GIF/MP4 저장 위치
  @Column(length = 2000)
  private String summary;          // 요약/설명 텍스트
  @Column(length = 2000)
  private String errorMessage;     // 실패 시 에러 메시지

  @Builder.Default
  private Instant createdAt = Instant.now();
  
  private Instant startedAt;
  private Instant finishedAt;
}
