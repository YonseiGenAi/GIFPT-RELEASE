package com.gifpt.file.domain;

import com.gifpt.user.domain.User;
import jakarta.persistence.*;
import lombok.*;

import java.time.Instant;

@Entity
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
@Table(name = "uploaded_files")
public class UploadFile {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false)
    private String fileName;

    private String s3Url; // 나중에 S3로 바꾸면 활용 가능

    @Column(length = 2000)
    private String prompt;

    @Builder.Default
    private Instant uploadedAt = Instant.now();
}
