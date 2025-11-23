package com.gifpt.workspace.domain;

import com.gifpt.analysis.domain.AnalysisJob;
import com.gifpt.user.domain.User;
import jakarta.persistence.*;
import lombok.*;

import java.time.OffsetDateTime;

@Entity
@Table(name = "workspace")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Workspace {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    // 워크스페이스를 만든 유저
    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User owner;

    @Column(nullable = false, length = 255)
    private String title;

    @Column(nullable = false, length = 2000)
    private String prompt;

    // 서버 로컬/볼륨 상 PDF 경로
    @Column(nullable = false, length = 1000)
    private String pdfPath;

    // Django 분석 Job (1:1)
    @OneToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "analysis_job_id")
    private AnalysisJob analysisJob;

    // 요약 결과 (Django 콜백에서 채움)
    @Column(columnDefinition = "TEXT")
    private String summary;

    // 최종 영상 URL (S3 주소 등)
    @Column(length = 1000)
    private String videoUrl;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 30)
    private WorkspaceStatus status;

    @Column(nullable = false)
    private OffsetDateTime createdAt;

    @Column(nullable = false)
    private OffsetDateTime updatedAt;

    @PrePersist
    void onCreate() {
        var now = OffsetDateTime.now();
        this.createdAt = now;
        this.updatedAt = now;
        if (this.status == null) {
            this.status = WorkspaceStatus.PENDING;
        }
    }

    @PreUpdate
    void onUpdate() {
        this.updatedAt = OffsetDateTime.now();
    }

    public enum WorkspaceStatus {
        PENDING,   // 분석 요청 보낸 상태
        RUNNING,   // Django/Worker에서 처리 중
        SUCCESS,   // 요약/영상 생성 완료
        FAILED     // 실패
    }
}
