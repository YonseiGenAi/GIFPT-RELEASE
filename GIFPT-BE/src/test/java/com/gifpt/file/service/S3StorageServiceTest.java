package com.gifpt.file.service;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.HeadObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadObjectResponse;
import software.amazon.awssdk.services.s3.model.NoSuchKeyException;
import software.amazon.awssdk.services.s3.model.S3Exception;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class S3StorageServiceTest {

    @Mock
    private S3Client s3Client;

    private S3StorageService service;

    @BeforeEach
    void setUp() {
        service = new S3StorageService(s3Client, "gifpt-demo", "https://gifpt-demo.s3.amazonaws.com");
    }

    @Test
    void objectExists_objectPresent_returnsTrue() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenReturn(HeadObjectResponse.builder().build());

        assertThat(service.objectExists("animations/abc123.mp4")).isTrue();
    }

    @Test
    void objectExists_objectMissing_returnsFalse() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenThrow(NoSuchKeyException.builder().message("Not Found").build());

        assertThat(service.objectExists("animations/missing.mp4")).isFalse();
    }

    @Test
    void objectExists_s3SdkError_propagates() {
        when(s3Client.headObject(any(HeadObjectRequest.class)))
                .thenThrow(S3Exception.builder().message("Access Denied").statusCode(403).build());

        assertThatThrownBy(() -> service.objectExists("animations/denied.mp4"))
                .isInstanceOf(S3Exception.class);
    }
}
