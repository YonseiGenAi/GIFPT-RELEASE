package com.gifpt.file.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;

import java.io.File;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;

@Service
public class S3StorageService {

    private final S3Client s3Client;
    private final String bucket;
    private final String baseUrl;

    public S3StorageService(
        S3Client s3Client,
        @Value("${gifpt.s3.bucket}") String bucket,
        @Value("${gifpt.s3.base-url}") String baseUrl
    ) {
        this.s3Client = s3Client;
        this.bucket = bucket;
        this.baseUrl = baseUrl;
    }

    public String uploadFile(File file, String keyPrefix) {
        // key 예: videos/2025/11/16/job-1234.mp4
        String timestamp = LocalDateTime.now()
            .format(DateTimeFormatter.ofPattern("yyyy/MM/dd/HHmmss"));
        String key = keyPrefix + "/" + timestamp + "-" + file.getName();

        PutObjectRequest putReq = PutObjectRequest.builder()
            .bucket(bucket)
            .key(key)
            .contentType("video/mp4") // 필요시 파라미터로 받기
            .build();

        s3Client.putObject(putReq, RequestBody.fromFile(file.toPath()));

        return baseUrl + "/" + key;  // 👉 이 URL을 DB나 콜백에 저장
    }

    /**
     * Check whether an object exists in S3 using a HEAD request (~50ms, no download).
     *
     * @param key S3 object key, e.g. "animations/abc123.mp4"
     * @return true if the object exists, false if it does not
     */
    public boolean objectExists(String key) {
        try {
            s3Client.headObject(HeadObjectRequest.builder()
                    .bucket(bucket)
                    .key(key)
                    .build());
            return true;
        } catch (NoSuchKeyException e) {
            return false;
        }
    }
}
